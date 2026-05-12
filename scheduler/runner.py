import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import redis
from django.conf import settings
from django.utils import timezone as djtz

from .models import Run, RunStatus

CHANNEL_PREFIX = "opentanuki:run:"
DONE_TOKEN = "__OPENTANUKI_DONE__"

AUTH_FAIL_PATTERNS = (
    "invalid api key",
    "authentication_error",
    "not authenticated",
    "please run `claude /login`",
    "please run /login",
    "claude /login",
    "claude auth login",
    "401 unauthorized",
    "oauth token expired",
    "credit balance is too low",
    "subscription required",
    "no api key",
    "api key not found",
)


def _looks_like_auth_fail(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in AUTH_FAIL_PATTERNS)


def _extract_session_id(line: str) -> str:
    s = line.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return ""
    try:
        obj = json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return ""
    sid = obj.get("session_id")
    return sid if isinstance(sid, str) else ""


def _redis() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def channel_for(run_id: int) -> str:
    return f"{CHANNEL_PREFIX}{run_id}"


def execute_run(run_id: int) -> None:
    run = Run.objects.select_related("task").get(pk=run_id)
    task = run.task
    argv = task.build_argv()
    log_path = Path(settings.RUN_LOG_DIR) / f"run-{run_id}.log"
    cwd = task.working_dir or os.path.expanduser("~")
    if not Path(cwd).is_dir():
        run.status = RunStatus.FAILED
        run.exit_code = -1
        run.started_at = djtz.now()
        run.finished_at = djtz.now()
        run.argv_json = json.dumps(argv)
        run.log_path = str(log_path)
        run.save()
        log_path.write_text(f"[opentanuki] working_dir does not exist: {cwd}\n")
        return

    r = _redis()
    run.status = RunStatus.RUNNING
    run.started_at = djtz.now()
    run.argv_json = json.dumps(argv)
    run.log_path = str(log_path)
    run.save()

    header = f"[opentanuki] cwd={cwd}\n[opentanuki] argv={json.dumps(argv)}\n"
    log_f = open(log_path, "w", buffering=1)
    log_f.write(header)
    r.publish(channel_for(run_id), header)

    env = os.environ.copy()
    env.setdefault("CLAUDE_CODE_NON_INTERACTIVE", "1")
    from .models import Setting
    oauth_token = "".join(Setting.get("claude_code_oauth_token", "").split())
    if oauth_token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token
        env.pop("ANTHROPIC_API_KEY", None)
    api_key = "".join(Setting.get("anthropic_api_key", "").split())
    if api_key and not oauth_token:
        env["ANTHROPIC_API_KEY"] = api_key

    auth_fail = False
    session_id = ""
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        run.pid = proc.pid
        run.save(update_fields=["pid"])
        assert proc.stdout is not None
        for line in proc.stdout:
            log_f.write(line)
            r.publish(channel_for(run_id), line)
            if not auth_fail and _looks_like_auth_fail(line):
                auth_fail = True
            sid = _extract_session_id(line)
            if sid:
                session_id = sid
        proc.wait()
        exit_code = proc.returncode
    except FileNotFoundError as e:
        msg = f"[opentanuki] claude binary not found: {e}\n"
        log_f.write(msg)
        r.publish(channel_for(run_id), msg)
        exit_code = 127
    except Exception as e:
        msg = f"[opentanuki] runner error: {e}\n"
        log_f.write(msg)
        r.publish(channel_for(run_id), msg)
        exit_code = -1
    finally:
        log_f.close()

    run.exit_code = exit_code
    run.finished_at = djtz.now()
    run.status = RunStatus.SUCCESS if exit_code == 0 else RunStatus.FAILED
    run.auth_required = auth_fail and run.status == RunStatus.FAILED
    run.save()
    if (
        task.continue_conversation
        and session_id
        and run.status == RunStatus.SUCCESS
        and session_id != task.claude_session_id
    ):
        task.claude_session_id = session_id
        task.save(update_fields=["claude_session_id", "updated_at"])
    suffix = " auth_required=1" if run.auth_required else ""
    r.publish(channel_for(run_id), f"\n[opentanuki] exit={exit_code} status={run.status}{suffix}\n")
    r.publish(channel_for(run_id), DONE_TOKEN)
