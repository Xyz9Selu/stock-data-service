## Why

Current local development setup does not provide a stable, reproducible database runtime, and service startup workflows are not standardized. We need a developer-friendly baseline that keeps Python service debugging local while making PostgreSQL environment portable and easy to migrate.

## What Changes

- Define a local development runtime model where PostgreSQL runs in Docker Compose and the Python service runs locally via `uv`.
- Define a persistent local bind-mount data directory for PostgreSQL so database state can be moved by copying project-local files.
- Define database port exposure policy so PostgreSQL can be reached by local host and other services inside the Tailscale network.
- Define standard startup, stop, reset, and migration execution workflows for local development.
- Define configuration boundaries for local service-to-container DB connectivity using environment variables.
- Add developer documentation requirements for Cursor-friendly command flow and troubleshooting.

## Capabilities

### New Capabilities
- `local-dev-db-compose`: Standardize local development runtime with Docker Compose PostgreSQL, local `uv` service process, local bind-mounted DB data, and startup/migration operational workflows.

### Modified Capabilities
- *(none)*

## Impact

- Affected runtime assets: `docker-compose.yml` (or equivalent compose file), environment templates, and developer documentation.
- Affected service startup behavior: local startup command sequence must include migration execution before app serve.
- No product API contract change, but local operational contract and bootstrap process become explicit and testable.
