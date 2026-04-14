## ADDED Requirements

### Requirement: Local development MUST run PostgreSQL via Docker Compose
The system SHALL provide a Docker Compose configuration that starts a PostgreSQL database service for local development without requiring a host-level PostgreSQL installation.

#### Scenario: Start local database service
- **WHEN** a developer runs the documented compose startup command for the database service
- **THEN** PostgreSQL container starts successfully and accepts TCP connections on the documented host port

#### Scenario: Stop local database service
- **WHEN** a developer runs the documented compose stop/down command
- **THEN** PostgreSQL container stops cleanly without corrupting persisted data files

#### Scenario: Tailscale peer service can access database port
- **WHEN** another service inside the same Tailscale network connects to the documented PostgreSQL host endpoint and port
- **THEN** PostgreSQL accepts the connection according to configured credentials and network access policy

### Requirement: Local PostgreSQL data MUST persist in a project-local bind mount
The system SHALL persist PostgreSQL data to a project-local directory through bind mount so data remains available across container recreation and can be migrated by copying files.

#### Scenario: Data survives container recreation
- **WHEN** a developer restarts or recreates the PostgreSQL container
- **THEN** previously written database records remain present because storage is read from the bind-mounted local directory

#### Scenario: Data directory is excluded from version control
- **WHEN** a developer checks repository tracking status
- **THEN** the configured local PostgreSQL data directory is not tracked as source-controlled files

### Requirement: Local service MUST run with uv against containerized database
The system SHALL define local service runtime using host execution (`uv`) connected to the compose PostgreSQL instance through environment configuration.

#### Scenario: Service connects to DB from host process
- **WHEN** a developer starts the service locally with documented environment variables
- **THEN** service establishes a successful database connection to the PostgreSQL container endpoint

#### Scenario: DB endpoint is environment-driven
- **WHEN** a developer changes configured host port or credentials in environment variables
- **THEN** service startup uses updated values without source code changes

### Requirement: Local startup MUST apply migrations before serving
The system SHALL enforce local startup workflow that executes database schema migrations before starting the API process.

#### Scenario: Fresh local environment bootstrap
- **WHEN** a developer starts service in an environment with an empty database
- **THEN** migration step runs first and creates required schema objects before API startup

#### Scenario: Migration failure blocks service startup
- **WHEN** migration execution fails during startup
- **THEN** service process does not continue to serve requests and outputs actionable error logs

### Requirement: Development workflow MUST include documented operational commands
The system SHALL provide documentation for local DB and service operations, including startup, stop, logs, reset, and troubleshooting steps compatible with terminal-based IDE workflows.

#### Scenario: New developer follows documented flow
- **WHEN** a new developer follows project documentation from clean checkout
- **THEN** they can bring up DB, start service, and reach a healthy local runtime without undocumented steps

#### Scenario: Developer performs local reset
- **WHEN** a developer intentionally executes documented reset steps
- **THEN** local database state is reset in a predictable way and next startup can reinitialize schema via migration

#### Scenario: Documentation explains network exposure boundaries
- **WHEN** a developer configures database exposure for Tailscale peer access
- **THEN** documentation clearly specifies required host bind behavior, security assumptions, and access-control guidance
