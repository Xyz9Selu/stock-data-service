# stock-data-service

A-share data service:

- **PostgreSQL sync** (full-market daily tables)
- **On-demand Tushare API** with disk cache (`/v1/*`)
- **Docker Compose** for `db + api`
- **MCP server** (stdio) for agent tools (OpenCode / Claude Desktop)

## Prerequisites

- Docker + Docker Compose plugin
- Python 3.13 + `uv` (host MCP / local dev)
- `TUSHARE_TOKEN` in `.env`

## 1) Configure

```bash
cp .env.example .env
# set TUSHARE_TOKEN, POSTGRES_PASSWORD, etc.
```

Defaults:

| Var | Default | Notes |
|-----|---------|--------|
| `APP_PORT` | `8002` | Host port for API |
| `POSTGRES_PORT` | `15432` | Host port for compose DB |
| `DATA_ROOT` | `/data/cache` in container | Bind: `./data/cache` |
| `STOCK_DATA_API` | `http://127.0.0.1:8002` | MCP / Serenity client |

## 2) Start with Docker Compose (recommended)

```bash
cd ~/stock-data-service
docker compose up -d --build
```

Services:

| Service | Container | Port |
|---------|-----------|------|
| `db` | `stock-data-service-db` | host `15432` → 5432 |
| `api` | `stock-data-service-api` | host `8002` → 8002 |

Useful commands:

```bash
docker compose ps
docker compose logs -f api
docker compose down          # keep volumes/bind data
curl -s http://127.0.0.1:8002/healthz | jq .
```

Cache files live on the host at `./data/cache/<api>/<hash>.json`.

Production (named volumes, DB not published):

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## 3) REST API (on-demand cache)

```bash
curl -s 'http://127.0.0.1:8002/healthz'
curl -s 'http://127.0.0.1:8002/v1/fina_mainbz?ts_code=600160.SH&type=P'
curl -s 'http://127.0.0.1:8002/v1/report_rc?ts_code=688498.SH&start_date=20250101'
curl -s 'http://127.0.0.1:8002/v1/cache/stats'
curl -s -X POST 'http://127.0.0.1:8002/v1/tushare/daily_basic' \
  -H 'Content-Type: application/json' \
  -d '{"params":{"ts_code":"688498.SH","trade_date":"20260714"}}'
```

`report_rc` live fetch is ~1/min; cache hits are free.

Serenity / other clients:

```bash
export STOCK_DATA_API=http://127.0.0.1:8002
```

## 4) MCP server (for agents)

MCP talks to the **running HTTP API** over stdio. Start Compose API first.

### Run manually

```bash
cd ~/stock-data-service
uv sync
STOCK_DATA_API=http://127.0.0.1:8002 uv run python -m app.mcp.server
```

### OpenCode (`~/.config/opencode/opencode.jsonc`)

```jsonc
{
  "mcp": {
    "stock-data": {
      "type": "local",
      "command": [
        "uv", "run",
        "--directory", "/home/xyz/stock-data-service",
        "python", "-m", "app.mcp.server"
      ],
      "environment": {
        "STOCK_DATA_API": "http://127.0.0.1:8002"
      },
      "enabled": true
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "stock-data": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/xyz/stock-data-service",
        "python",
        "-m",
        "app.mcp.server"
      ],
      "env": {
        "STOCK_DATA_API": "http://127.0.0.1:8002"
      }
    }
  }
}
```

### Tools

| Tool | Purpose |
|------|---------|
| `health` | API / DB / token / cache |
| `fina_mainbz` | 主营构成 |
| `report_rc` | 券商研报（限频） |
| `daily_basic` | 估值/市值日频 |
| `stock_company` | 公司简介 |
| `tushare_query` | 任意 Tushare Pro API（JSON params） |
| `cache_stats` | 磁盘缓存统计 |
| `sync_status` / `sync_trigger` | 全市场 PG 同步 |

## 5) Local Python (without full Docker app)

DB only in Docker, app on host:

```bash
docker compose up -d db
# .env: POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=15432
uv sync
uv run python main.py start
```

## 6) Troubleshooting

- **Port 8002 in use**: stop host uvicorn (`pkill -f 'uvicorn main:app'`) or change `APP_PORT`.
- **MCP cannot connect**: ensure `docker compose ps` shows `api` healthy; `curl /healthz`.
- **DB not ready**: wait for `db` healthcheck; check `docker compose logs db`.
- **Empty Tushare**: set `TUSHARE_TOKEN` in `.env` and recreate: `docker compose up -d --force-recreate api`.
