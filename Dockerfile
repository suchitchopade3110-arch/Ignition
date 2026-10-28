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

FROM python:${PYTHON_VERSION}-slim AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin ignition
COPY --from=build /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /srv
COPY app ./app
USER 10001
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
# The backend's command; the worker service overrides it with
# `arq app.worker.WorkerSettings` (render.yaml dockerCommand).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
