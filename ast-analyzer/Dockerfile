FROM oven/bun:1-slim AS base

# git is needed at runtime: /analyze clones the target repo to analyze it.
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY package.json bun.lock ./
RUN bun install
COPY . .

# Internal-only — see server.ts, which binds 127.0.0.1 inside whatever
# network namespace this container has. In docker-compose that namespace
# is the private `ignition` network, not the host, so nothing outside the
# compose stack can reach this regardless of the loopback bind.
EXPOSE 4000
CMD ["bun", "run", "server.ts"]
