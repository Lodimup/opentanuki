import asyncio
import json
from pathlib import Path

from django.conf import settings
from django.http import StreamingHttpResponse
from redis import asyncio as aioredis

from .models import Run
from .runner import DONE_TOKEN, channel_for


def _format_sse(data: str, event: str | None = None, msg_id: int | None = None) -> str:
    lines = []
    if msg_id is not None:
        lines.append(f"id: {msg_id}")
    if event:
        lines.append(f"event: {event}")
    for ln in data.splitlines() or [""]:
        lines.append(f"data: {ln}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


def prettify_line(line: str) -> str:
    """Convert a stream-json or raw line to readable display text."""
    s = line.rstrip("\n")
    if not s.strip():
        return ""
    if not (s.lstrip().startswith("{") and s.rstrip().endswith("}")):
        return s
    try:
        obj = json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return s
    t = obj.get("type")
    if t == "system":
        sub = obj.get("subtype", "")
        model = obj.get("model", "")
        bits = [x for x in (sub, model) if x]
        return f"[system] {' '.join(bits)}" if bits else "[system]"
    if t == "assistant":
        msg = obj.get("message", {}) or {}
        out = []
        for block in msg.get("content", []) or []:
            bt = block.get("type")
            if bt == "text":
                txt = (block.get("text") or "").strip()
                if txt:
                    out.append(txt)
            elif bt == "thinking":
                txt = (block.get("thinking") or "").strip()
                if txt:
                    out.append(f"[thinking] {txt}")
            elif bt == "tool_use":
                name = block.get("name", "?")
                inp = block.get("input", {}) or {}
                summary = ""
                if "command" in inp:
                    summary = inp["command"]
                elif "file_path" in inp:
                    summary = inp["file_path"]
                elif "pattern" in inp:
                    summary = inp["pattern"]
                elif "url" in inp:
                    summary = inp["url"]
                summary = (summary or "")[:200]
                out.append(f"→ {name}({summary})")
        return "\n".join(out) if out else ""
    if t == "user":
        msg = obj.get("message", {}) or {}
        for block in msg.get("content", []) or []:
            if block.get("type") == "tool_result":
                content = block.get("content")
                if isinstance(content, list):
                    parts = []
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            parts.append(c.get("text", ""))
                    text = "\n".join(parts)
                else:
                    text = str(content or "")
                text = text.strip()
                if not text:
                    return ""
                truncated = text[:600] + ("…" if len(text) > 600 else "")
                return f"← result: {truncated}"
        return ""
    if t == "result":
        usage = obj.get("usage", {}) or {}
        cost = obj.get("total_cost_usd") or obj.get("cost_usd")
        bits = []
        if cost is not None:
            bits.append(f"cost=${float(cost):.4f}")
        if usage.get("input_tokens"):
            bits.append(f"in={usage['input_tokens']}")
        if usage.get("output_tokens"):
            bits.append(f"out={usage['output_tokens']}")
        return f"[result] {' '.join(bits)}" if bits else "[result]"
    return s


def _read_log_file(log_path: Path) -> list[str]:
    with open(log_path, "r") as f:
        return f.readlines()


async def stream_run(run_id, last_event_id: int = 0):
    """Async generator yielding SSE for a run, deduped by line counter.

    - Replays log file from line `last_event_id` onward (handles reconnect).
    - Parses stream-json into readable form when possible.
    - Subscribes to pubsub for live tail; emits ids continuing from file end.
    """
    run = await Run.objects.aget(pk=run_id)
    counter = 0
    log_path = Path(run.log_path) if run.log_path else None
    if log_path and log_path.exists():
        lines = await asyncio.to_thread(_read_log_file, log_path)
        for raw in lines:
            counter += 1
            if counter <= last_event_id:
                continue
            pretty = prettify_line(raw)
            if pretty == "":
                continue
            yield _format_sse(pretty, event="log", msg_id=counter)

    if not run.is_active:
        yield _format_sse(
            f"exit={run.exit_code} status={run.status}", event="done", msg_id=counter + 1
        )
        return

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(channel_for(run_id))

    try:
        loop = asyncio.get_event_loop()
        last_ping = loop.time()
        while True:
            msg = await pubsub.get_message(timeout=1.0)
            if msg is None:
                await run.arefresh_from_db()
                if not run.is_active:
                    counter += 1
                    yield _format_sse(
                        f"exit={run.exit_code} status={run.status}", event="done", msg_id=counter
                    )
                    return
                now = loop.time()
                if now - last_ping > 15:
                    yield ": keepalive\n\n"
                    last_ping = now
                continue
            data = msg.get("data", "")
            if data == DONE_TOKEN:
                await run.arefresh_from_db()
                counter += 1
                yield _format_sse(
                    f"exit={run.exit_code} status={run.status}", event="done", msg_id=counter
                )
                return
            for chunk in (data or "").splitlines():
                pretty = prettify_line(chunk)
                if pretty == "":
                    continue
                counter += 1
                yield _format_sse(pretty, event="log", msg_id=counter)
            last_ping = loop.time()
    finally:
        try:
            await pubsub.aclose()
        except Exception:
            pass
        try:
            await r.aclose()
        except Exception:
            pass


def sse_response(run_id, last_event_id: int = 0) -> StreamingHttpResponse:
    resp = StreamingHttpResponse(
        stream_run(run_id, last_event_id), content_type="text/event-stream"
    )
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp
