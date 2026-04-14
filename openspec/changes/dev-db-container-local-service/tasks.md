## 1. Compose Database Runtime

- [x] 1.1 Add a compose configuration that defines a PostgreSQL `db` service with healthcheck and host port mapping for local development.
- [x] 1.2 Configure PostgreSQL storage as a project-local bind-mounted directory (for example `./.local/postgres-data`) and ensure the directory is ignored by git.
- [x] 1.3 Configure and verify DB port exposure for both local host and Tailscale network peer service access.
- [x] 1.4 Document and verify DB lifecycle commands: start, stop, down, logs, and reset behavior.
- [x] 1.5 Add a dedicated production compose file where both `db` and `server` run as containers.

## 2. Local Service Connectivity and Startup Flow

- [x] 2.1 Add/update environment template variables so local host service can connect to containerized DB through `127.0.0.1:<port>`.
- [x] 2.2 Implement local service startup command flow that runs migrations before launching the API process via `uv`.
- [x] 2.3 Ensure migration failure stops service startup with actionable output and provide a standalone migration command for recovery.

## 3. Developer Experience and Documentation

- [x] 3.1 Update README (or equivalent docs) with a clean-start local workflow from clone to running service.
- [x] 3.2 Add troubleshooting notes for common issues: port conflict, bind-mount permissions, DB readiness timing, and Tailscale connectivity checks.
- [x] 3.3 Add migration and data portability guidance, including backup/restore baseline commands for local bind-mounted PostgreSQL data.
- [x] 3.4 Add security guidance for Tailscale-sharing mode, including recommended ACL/firewall boundaries.

## 4. Validation

- [x] 4.1 Validate fresh environment bootstrap: start DB container, run local service, auto-apply migrations, and confirm service can connect successfully.
- [x] 4.2 Validate persistence: create sample DB data, recreate container, and confirm data remains via bind mount.
- [x] 4.3 Validate reset flow: execute documented reset and confirm startup can rebuild schema from migrations.
- [ ] 4.4 Validate remote access path: from a Tailscale peer service, confirm DB connectivity using expected credentials.
