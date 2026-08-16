FROM python:3.12-slim AS base

# --- Bun runtime + git (repo cloning) + unzip (zip-source extraction) ---
RUN apt-get update && apt-get install -y curl unzip git && \
    curl -fsSL https://bun.sh/install | bash && \
    ln -s /root/.bun/bin/bun /usr/local/bin/bun && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# --- Python side ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# --- Bun side (persistent AST service, not per-PR subprocess) ---
COPY ast-analyzer ./ast-analyzer
RUN cd ast-analyzer && bun install

# Both processes are supervised by a tiny entrypoint script rather than a
# full process manager, since it's just these two long-running services.
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Only 8000 (FastAPI) is meant to be reachable from outside the container.
# The Bun AST analyzer on 4000 is internal-only (see ast-analyzer/server.ts
# — it now binds 127.0.0.1) and must never be published by whatever
# platform runs this image.
EXPOSE 8000
CMD ["./docker-entrypoint.sh"]