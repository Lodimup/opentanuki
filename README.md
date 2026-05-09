# OpenTanuki

Self-hosted scheduler for `claude -p`. Run Claude Code on cron, interval, or manual triggers. Live-stream output via SSE. Per-user task isolation. SQLite + Redis. Neobrutalism UI.

Each run starts inside a working directory you choose, so it inherits the full Claude Code surface area for that project — `CLAUDE.md`, `.claude/skills/`, `.claude/agents/`, `.claude/settings.json`, MCP servers, hooks, and slash commands all apply automatically. Stage the workdir like you would for an interactive Claude Code session and the scheduled run gets the same capabilities.

OpenTanuki will grow to be your personal assistant, but for now a scheduler :)

![Dashboard](docs/screenshots/dashboard.png)

## Stack

- Django 6 + sqlite + htmx + Tailwind (CDN) + Space Grotesk
- Celery + Redis (worker + beat)
- Granian (ASGI) + WhiteNoise
- pydantic-settings
- django-ninja for JSON API

## Quick start

```bash
cp .env.example .env       # set DJANGO_SECRET_KEY
make install               # uv sync
make redis                 # docker compose up -d redis
make migrate
make user                  # createsuperuser
```

Run in 3 terminals:

```bash
make web                   # granian on PORT (default 8888)
make worker                # celery worker
make beat                  # celery beat
```

Open http://127.0.0.1:8888

## Sample use cases

| Schedule | Prompt | Why |
|---|---|---|
| `0 8 * * *` (cron) | "Research today's world news. Summarize top 5 in 2 sentences each. `say` summary aloud." | Morning briefing read aloud while making coffee |
| `*/30 * * * *` (interval 1800s) | "Fetch BTC + ETH + SOL spot price. Compare to 24h ago. `say` deltas." | Background market pulse |
| `0 9 * * 1` (cron) | "`uv pip list --outdated`. Pick top 3 with breaking-change risk. Write to `~/Desktop/dep-audit.md`." | Monday dependency review |
| every 1h | "Read latest 20 emails from `~/Mail`. Group by sender, flag urgent. Output ranked action list." | Inbox triage loop |
| manual | "Check git status of project. Print uncommitted file count + diverged commit count vs origin." | Pre-deploy gate |

Each task runs `claude -p <prompt>` in its own working directory with full CLI flag coverage (`--model`, `--permission-mode`, `--allowedTools`, `--add-dir`, `--max-budget-usd`, etc).

### About `say`

`say` is the macOS built-in text-to-speech command (`/usr/bin/say`). Claude can shell out to it to read summaries aloud — handy for ambient briefings while you're not at the keyboard. No setup, no API keys, runs offline. Default voices are robotic.

**Recommended: enable Siri voices.** System Settings → Accessibility → Spoken Content → System Voice → Manage Voices, then download "Siri Voice 1" / "Siri Voice 2" / etc. set as default - far more natural than the legacy voices.

```bash
say "morning briefing ready"                # list installed voices
```

For higher-quality or cross-platform speech, swap `say` for one of these in your prompts:

- **[Kokoro TTS](https://github.com/hexgrad/kokoro)** — 82M-param open-weights neural TTS. Local, fast (CPU-viable), surprisingly natural. Run via `pip install kokoro` then call from a tiny wrapper script. Best when you want fully offline + free.
- **[Qwen TTS (local)](https://qwen.ai/blog?id=qwen3tts-0115)** — run Qwen2.5-Omni locally (3B or 7B) for expressive multilingual TTS without sending audio to a vendor. Strong prosody, supports Chinese + English + Japanese + Korean. Heavier than Kokoro but worth it for non-English or longer-form narration. Best when you want broadcast-grade voice on your own hardware.

In a task prompt: `... write summary to /tmp/brief.txt, then run \`./speak.sh /tmp/brief.txt\`` — your `speak.sh` invokes whichever backend you prefer.

## Screens

### Login
![Login](docs/screenshots/login.png)

### Dashboard
Favorites pinned, search across name/prompt/dir, recent runs table polls live.

![Dashboard](docs/screenshots/dashboard.png)

### Task detail
Run history table updates every 2s. Run-now button disabled while task active.

![Task detail](docs/screenshots/task_detail.png)

### New / edit task
Full claude `-p` arg surface. Cron entered in local timezone, stored UTC.

![Task form](docs/screenshots/task_form.png)

## Layout

```
app/                       # Django project
  app_settings.py          # pydantic-settings groups
  settings.py              # reads APP_SETTINGS
scheduler/
  models/                  # one model per file
    task.py setting.py run.py _base.py
  routes/                  # ninja routes, one verb per file
    dashboard/get_index.py
    tasks/get_runs.py
    tasks/post_trigger.py
  views/                   # one Django view per file
  templates/scheduler/
  tests.py                 # 94 tests, 88% coverage
```

## Why no Dockerfile?

OpenTanuki is meant to run on the host, not in a container. Each task spawns `claude -p` inside a working directory you choose, and Claude routinely needs the full power of the host OS to be useful — local binaries (`say`, `osascript`, `git`, `ffmpeg`, `uv`), system services (Mail, Calendar, Music), MCP servers that talk to the OS, GUI automations, GPU/Metal access, USB / Bluetooth peripherals, and so on. Stuffing all that into a container would either break those capabilities or require a tangle of bind mounts, host networking, and privileged flags that defeats the point.

The right boundary is the host's own sandbox layer. On macOS, run OpenTanuki under a dedicated user account, lean on Full Disk Access prompts, App Sandbox / TCC, and per-app screen recording / accessibility grants to scope what it can touch. On Linux, use a separate user plus systemd unit hardening (`ProtectHome`, `ReadOnlyPaths`, `NoNewPrivileges`, namespaces). That gives Claude full reach into the things it needs while keeping the rest of the system off-limits — a cleaner trade than Docker for an agent whose whole job is to act on the machine it runs on.

Or even better, grab a used Mac Mini, make that your tanuki's new home.

Containers still make sense for the side services (Redis is already in `docker-compose.yml`); the Django + Celery + `claude` processes belong on the host.

## Auth

Per-user isolation enforced at every query: `task__user=request.user`. Cross-user reads return 404. Tasks fan out into Celery beat as user-tagged `PeriodicTask` rows; runs inherit the task's user via FK.

## Settings + secrets

`Setting` model stores OAuth token / API key in sqlite for the worker to inject as env vars before `claude -p`. Plain text — protect host. Set via `/settings/` UI.

## Test

```bash
make test                  # 94 tests
```

## License

MIT.
