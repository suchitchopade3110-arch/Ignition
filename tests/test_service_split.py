"""
I-3 / I-9: one Render service per process, and images that are built to
run as services. Static checks of render.yaml, both Dockerfiles and CI
(the images themselves are built by CI's docker-build job and, here,
listed in HUMAN_ACTIONS: this sandbox has no Docker daemon).
"""
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
BLUEPRINT = yaml.safe_load((REPO / "render.yaml").read_text())
SERVICES = {s["name"]: s for s in BLUEPRINT["services"]}
BACKEND_DOCKERFILE = (REPO / "Dockerfile").read_text()
ANALYZER_DOCKERFILE = (REPO / "ast-analyzer" / "Dockerfile").read_text()
CI = (REPO / ".github" / "workflows" / "ci.yml").read_text()


def _env(service: dict) -> dict:
    return {e["key"]: e for e in service.get("envVars", [])}


# --- render.yaml -------------------------------------------------------------

def test_five_services_with_the_doc_types_and_plans():
    expected = {
        "ignition-frontend": ("web", "0.5c-512mb"),
        "ignition-backend": ("web", "0.5c-512mb"),
        "ignition-worker": ("worker", "1c-2g"),
        "ignition-analyzer": ("pserv", "1c-2g"),
        "ignition-redis": ("keyvalue", "starter"),
    }
    assert {name: (s["type"], s.get("plan")) for name, s in SERVICES.items()} == expected


def test_backend_runs_uvicorn_only_and_worker_runs_arq_only():
    backend, worker = SERVICES["ignition-backend"], SERVICES["ignition-worker"]
    assert backend["runtime"] == worker["runtime"] == "docker"
    assert backend["dockerCommand"].startswith("uvicorn app.main:app")
    assert worker["dockerCommand"] == "arq app.worker.WorkerSettings"
    assert worker["maxShutdownDelaySeconds"] == 60


def test_analyzer_is_private_and_listens_on_all_interfaces():
    analyzer = SERVICES["ignition-analyzer"]
    assert analyzer["dockerfilePath"] == "./ast-analyzer/Dockerfile"
    env = _env(analyzer)
    assert env["AST_ANALYZER_HOST"]["value"] == "0.0.0.0"
    assert env["AST_WORKSPACES_ROOT"]["value"]


@pytest.mark.parametrize("name", ["ignition-backend", "ignition-worker"])
def test_python_services_reach_redis_and_the_analyzer_privately(name):
    env = _env(SERVICES[name])
    assert env["REDIS_URL"]["fromService"] == {"type": "keyvalue", "name": "ignition-redis",
                                                "property": "connectionString"}
    assert env["AST_SERVICE_URL"]["fromService"] == {"type": "pserv", "name": "ignition-analyzer",
                                                      "property": "hostport"}


def test_redis_is_internal_and_never_evicts_jobs():
    redis = SERVICES["ignition-redis"]
    assert redis["ipAllowList"] == [] and redis["maxmemoryPolicy"] == "noeviction"


def test_ast_client_accepts_a_bare_private_hostport():
    # Render's fromService hostport is "host:port", without a scheme.
    from app.services.ast_client import ASTClient
    assert ASTClient(base_url="ignition-analyzer-abc1:4000")._base_url == "http://ignition-analyzer-abc1:4000"
    assert ASTClient(base_url="http://localhost:4000/")._base_url == "http://localhost:4000"


# --- images ------------------------------------------------------------------

@pytest.mark.parametrize("dockerfile", [BACKEND_DOCKERFILE, ANALYZER_DOCKERFILE], ids=["backend", "analyzer"])
def test_images_are_multi_stage_non_root_and_run_under_tini(dockerfile):
    assert len(re.findall(r"^FROM ", dockerfile, re.M)) >= 2
    assert re.search(r"^USER 10001$", dockerfile, re.M)
    assert re.search(r'^ENTRYPOINT \["/usr/bin/tini", "--"\]$', dockerfile, re.M)
    runtime_stage = dockerfile.split("AS runtime", 1)[1]
    assert "curl" not in runtime_stage and "wget" not in runtime_stage


def test_only_the_analyzer_image_has_git():
    assert "git" not in re.sub(r"#.*", "", BACKEND_DOCKERFILE)
    assert re.search(r"apt-get install[^\n]*\bgit\b", ANALYZER_DOCKERFILE)


def test_python_image_installs_into_a_venv_with_hashes():
    assert "python -m venv /opt/venv" in BACKEND_DOCKERFILE
    assert "--require-hashes" in BACKEND_DOCKERFILE


def test_one_python_version_in_docker_and_ci():
    docker = re.search(r"^ARG PYTHON_VERSION=(\S+)$", BACKEND_DOCKERFILE, re.M).group(1)
    ci_versions = set(re.findall(r'python-version: "([^"]+)"', CI))
    assert ci_versions == {docker}


def test_bun_is_copied_from_a_pinned_image_and_ci_pins_the_same_version():
    pinned = re.search(r"^ARG BUN_VERSION=(\d+\.\d+\.\d+)$", ANALYZER_DOCKERFILE, re.M).group(1)
    stage = re.search(r"^FROM oven/bun:\$\{BUN_VERSION\}\S* AS (\w+)$", ANALYZER_DOCKERFILE, re.M).group(1)
    assert f"COPY --from={stage} /usr/local/bin/bun /usr/local/bin/bun" in ANALYZER_DOCKERFILE
    ci_pins = set(re.findall(r"bun-version: (\S+)", CI))
    assert ci_pins == {pinned}


def test_worker_drain_fits_inside_renders_shutdown_delay():
    from app.worker import WorkerSettings
    assert WorkerSettings.job_completion_wait == 50
    assert WorkerSettings.job_completion_wait < SERVICES["ignition-worker"]["maxShutdownDelaySeconds"]
