# Python image for ignition-backend (uvicorn) and ignition-worker (arq):
# one image, two Render services, each process PID 1 under tini (I-3).
# Multi-stage, installs into a venv, runs as UID 10001, no curl or git (I-9).
# PYTHON_VERSION must match CI's python-version (tests/test_service_split.py).
ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt /tmp/requirements.txt
RUN pip install --require-hashes -r /tmp/requirements.txt
# Bake the embedding model into the image (I-1): the worker never downloads
# it at runtime, and runs with HF_HUB_OFFLINE=1.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2', cache_dir='/opt/models')"

FROM python:${PYTHON_VERSION}-slim AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin ignition
COPY --from=build /opt/venv /opt/venv
COPY --from=build /opt/models /opt/models
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    FASTEMBED_CACHE_PATH=/opt/models HF_HUB_OFFLINE=1
WORKDIR /srv
COPY app ./app
# One-off maintenance run from the worker's shell (I-1 re-embed).
COPY scripts/reembed_incidents.py ./scripts/reembed_incidents.py
USER 10001
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
# The backend's command; the worker service overrides it with
# `arq app.worker.WorkerSettings` (render.yaml dockerCommand).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
