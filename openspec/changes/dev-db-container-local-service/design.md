## Context

The project currently has no standardized local runtime for database and service startup. We want a development model that preserves fast local Python iteration and debugger compatibility while avoiding local PostgreSQL installation drift. The team also requires database portability for environment migration by copying local project files.

This change introduces a split runtime: PostgreSQL runs in Docker Compose, while the service runs locally via `uv`. Local development must remain deterministic, easy to start/stop in Cursor terminal workflows, and easy to reset or migrate.

## Goals / Non-Goals

**Goals:**
- Standardize a local development runtime where PostgreSQL is managed by Docker Compose and the service runs locally.
- Persist PostgreSQL data in a project-local bind-mounted directory for straightforward migration and backup.
- Expose PostgreSQL port for both host-local access and controlled access from other services in the Tailscale network.
- Ensure local service startup includes automatic migration execution before serving.
- Define operational commands for startup, shutdown, logs, reset, and health checks.
- Keep configuration explicit through environment variables and documentation.

**Non-Goals:**
- Containerizing the Python service for the default local development loop.
- Defining production deployment topology.
- Introducing DB foreign keys or enum database types.
- Changing business APIs or sync business logic in this change.

## Decisions

### 1. Development runtime split: containerized DB, local service
**Decision**: Run only PostgreSQL in Docker Compose (`db` service). Run Python service on host using `uv run ...`.

**Rationale**: This gives the best local debugging and single-step tracing experience while keeping DB runtime reproducible. It also reduces compose complexity and avoids inner-loop rebuild friction.

**Alternatives considered**:
- Full containerized `db + service`: rejected for local default because debugger/reload flow is less direct.
- Fully local DB and service: rejected due to environment drift and migration friction.

### 2. PostgreSQL data persistence via project-local bind mount
**Decision**: Map PostgreSQL data directory to a project-local path (for example, `./.local/postgres-data`), excluded from git.

**Rationale**: Migration becomes a file copy operation. Data survives container recreation and can be versioned operationally through backup scripts.

**Alternatives considered**:
- Named Docker volumes: simpler Docker UX, but less transparent for direct migration workflows.
- Host-global path outside project: rejected for portability and onboarding clarity.

### 3. Migration execution on local service startup
**Decision**: Local startup flow SHALL run DB migrations first, then start the service process.

**Rationale**: Developers should not need manual migration steps to get a runnable environment. Startup-time migration ensures schema and code stay aligned.

**Alternatives considered**:
- Manual migration command: rejected due to frequent drift and onboarding errors.
- Dedicated migration container: good for production CI/CD but unnecessary complexity for local default.

### 4. Compose readiness and operational ergonomics
**Decision**: Compose configuration SHALL include PostgreSQL healthcheck and documented command conventions compatible with Cursor terminal usage.

**Rationale**: Health checks reduce transient startup failures. Consistent commands improve day-to-day team efficiency and reduce environment-specific tribal knowledge.

### 5. Configuration boundary
**Decision**: Local service connects to DB via host endpoint (`127.0.0.1:<mapped-port>`) using environment variables in `.env`.

**Rationale**: Because service runs on host, Compose network aliases are not available. Explicit host/port keeps behavior predictable.

### 6. Tailscale network accessibility for PostgreSQL
**Decision**: PostgreSQL host port SHALL be published so it can be accessed from local host and from selected services inside the Tailscale network, with explicit documentation on access control boundaries.

**Rationale**: The user requires DB sharing for additional internal services over Tailscale while retaining a simple local development workflow. Explicit exposure rules avoid accidental "local-only" assumptions.

**Alternatives considered**:
- Localhost-only bind (`127.0.0.1:5432:5432`): rejected because it blocks remote Tailscale peers.
- Full public internet exposure: rejected for security reasons and outside development intent.

## Risks / Trade-offs

- [Local bind mount permissions mismatch] → Mitigation: document directory ownership/permission expectations and first-run troubleshooting.
- [Accidental data deletion in local mounted directory] → Mitigation: provide explicit reset commands and backup guidance before destructive actions.
- [Automatic migration failure blocks startup] → Mitigation: fail fast with clear logs and a standalone migration command for recovery.
- [Port conflicts on PostgreSQL host port] → Mitigation: support override via environment variable and document conflict resolution.
- [Unexpected network exposure due to broad port bind] → Mitigation: document firewall/Tailscale ACL expectations and recommended bind strategy for development environments.
- [Divergence from future production topology] → Mitigation: keep migration and config interfaces environment-agnostic to preserve portability.

## Migration Plan

1. Add compose configuration for `db` service with bind-mounted data directory and healthcheck.
2. Define environment variables and update `.env.example` for local service DB connectivity and Tailscale-reachable host/port settings.
3. Add local startup command flow: run migrations then start service with `uv`.
4. Add documentation for startup/stop/logs/reset/backup workflows.
5. Validate from empty state: bring up DB, run service, apply migrations, perform basic DB connectivity checks.

Rollback:
- Stop using compose DB and return to prior local DB workflow.
- Preserve mounted data directory to avoid accidental data loss.
- Revert runtime and docs changes if needed.

## Open Questions

- Should we provide a helper script/Makefile target for one-command local startup, or keep raw commands only?
- Should default DB port remain `5432`, or use a project-specific port to reduce conflicts on developer machines?
- Do we want a lightweight automatic backup command in the first iteration, or only document manual `pg_dump` usage?
