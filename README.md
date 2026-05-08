# OpenTanuki 🦝

Schedule `claude -p` runs on cron / interval / manual triggers. Live-stream output via SSE.

## Stack

- Django 5 + sqlite + htmx + tailwind (CDN) + Space Grotesk (neobrutalism)
- Celery + Redis (worker + beat) for scheduling
- `subprocess.Popen` + redis pubsub for live log streaming

## Run

```bash
# 1. Boot redis
docker compose up -d redis

# 2. Install deps
uv sync

# 3. Migrate + create superuser
uv run python manage.py migrate
uv run python manage.py createsuperuser

# 4. Start everything (3 terminals)
uv run granian --interface asginl app.asgi:application --host 127.0.0.1 --port 8888 --reload
uv run celery -A app worker -l info
uv run celery -A app beat -l info -S django
```

Open http://127.0.0.1:8888

## Features

- Full claude `-p` arg coverage: model, permission-mode, allowedTools, disallowedTools, add-dir, output-format, dangerously-skip-permissions, max-budget-usd, free-form extra args
- Working dir picker with server-side directory browser
- Schedule modes: manual / interval / cron (5 fields, UTC)
- Manual run trigger (▶ button) on every task
- Live log streaming via htmx-ext-sse during `running` state
- Run history per task with exit code + duration
- Logs persisted to `data/runs/run-<id>.log`
