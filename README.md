# stock-data-service

Local development uses:
- PostgreSQL in Docker Compose.
- Python service on host with `uv`.
- Production compose uses both `db + app` containers.

## Prerequisites

- Docker and Docker Compose plugin.
- Python 3.13 and `uv`.
- Tailscale configured if you need remote peer access.

## 1) Configure environment

Copy and edit environment values:

```bash
cp .env.example .env
```

Important DB values:
- `POSTGRES_HOST=127.0.0.1`
- `POSTGRES_PORT=15432`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`

## 2) Start and manage database container

Start DB:

```bash
docker compose up -d db
```

Check logs:

```bash
docker compose logs -f db
```

Stop DB:

```bash
docker compose stop db
```

Remove container (keeps data):

```bash
docker compose down
```

Reset DB data (destructive):

```bash
docker compose down
rm -rf ./.local/postgres-data
docker compose up -d db
```

## 3) Run migrations and service locally

Install dependencies:

```bash
uv sync
```

Run migrations only:

```bash
uv run python main.py migrate
```

Run service only:

```bash
uv run python main.py serve
```

Run default startup flow (migrate then serve):

```bash
uv run python main.py start
```

Migration errors stop startup immediately with non-zero exit code.

## 4) On-demand query cache (Serenity)

Besides full-market daily sync into PostgreSQL, the service exposes **disk-cached** Tushare queries:

```bash
# after serve is up (default port from .env APP_PORT, often 8002)
curl 'http://127.0.0.1:8002/v1/fina_mainbz?ts_code=600160.SH&type=P'
curl 'http://127.0.0.1:8002/v1/report_rc?ts_code=688498.SH&start_date=20250101'
curl 'http://127.0.0.1:8002/v1/cache/stats'
# generic
curl -X POST 'http://127.0.0.1:8002/v1/tushare/daily_basic' \
  -H 'Content-Type: application/json' \
  -d '{"params":{"ts_code":"688498.SH","trade_date":"20260714"}}'
```

Cache files: `data/cache/<api_name>/<hash>.json` (gitignored).  
`report_rc` is rate-limited (~61s between live fetches); cache hits are free.

Serenity client: `export STOCK_DATA_API=http://127.0.0.1:8002`

## 5) Validation checklist

Fresh bootstrap:
1. `docker compose up -d db`
2. `uv run python main.py start`
3. Visit `http://127.0.0.1:${APP_PORT}/healthz`

Persistence check:
1. Connect to DB and create test row.
2. `docker compose down` then `docker compose up -d db`
3. Confirm test row still exists.

## 6) Tailscale peer access

By default compose maps `${POSTGRES_PORT}:5432`, which allows remote access on host interfaces.
To use from another Tailscale node, connect to:
- host: `<tailscale-ip>`
- port: `POSTGRES_PORT`

Recommended security boundaries:
- Restrict inbound firewall rules to `tailscale0` and trusted peers.
- Use Tailscale ACLs to allow only specific services/users to reach PostgreSQL port.
- Use strong non-default DB credentials.
- Do not expose this DB port to the public internet.

## 7) Troubleshooting

- Port conflict (`address already in use`): change `POSTGRES_PORT` in `.env` and restart DB.
- Permission issue on `.local/postgres-data`: ensure current user can read/write this directory.
- DB not ready: wait for `docker compose ps` health status `healthy`.
- Tailscale peer cannot connect: verify ACLs, firewall, and that peer can reach your Tailscale IP.

## 8) Data migration backup/restore

Backup:

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > backup.sql
```

Restore:

```bash
cat backup.sql | docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

## 9) Production compose (`db + app`)

Start production stack:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

View logs:

```bash
docker compose -f docker-compose.prod.yml logs -f
```

Stop production stack:

```bash
docker compose -f docker-compose.prod.yml down
```

Notes:
- In production compose, app connects to DB through internal host `db:5432`.
- `APP_PORT` controls host exposure for API.
- DB data uses managed volume `pg_data_prod`.
