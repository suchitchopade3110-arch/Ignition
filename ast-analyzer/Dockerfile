# ignition-analyzer: Bun + ts-morph, a Render private service (pserv) that
# only the worker reaches (I-3). The only image with git: /analyze fetches
# the reviewed repo. Bun is copied from a pinned image; CI pins the same
# version (tests/test_service_split.py). Runs as UID 10001 under tini (I-9).
ARG BUN_VERSION=1.4.4

FROM oven/bun:${BUN_VERSION}-slim AS bun
WORKDIR /srv
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile --production

FROM debian:bookworm-slim AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin ignition \
    && mkdir -p /srv/workspaces && chown 10001:10001 /srv/workspaces
COPY --from=bun /usr/local/bin/bun /usr/local/bin/bun
WORKDIR /srv
COPY --from=bun /srv/node_modules ./node_modules
COPY package.json tsconfig.json server.ts analyzer.ts source.ts ./
# Mirrors and per-review worktrees (P0-3); render.yaml sets the same path.
ENV AST_WORKSPACES_ROOT=/srv/workspaces
USER 10001
# Listens on 4000; AST_ANALYZER_HOST=0.0.0.0 is set by render.yaml (a
# private service) and docker-compose (a private network).
EXPOSE 4000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bun", "run", "server.ts"]
