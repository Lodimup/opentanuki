from asgiref.sync import sync_to_async
from django.db.models import Exists, OuterRef
from django.shortcuts import render as _render
from django.template.loader import render_to_string as _render_to_string

from ..models import Run, RunStatus

SETTING_KEYS = ("claude_code_oauth_token", "anthropic_api_key")

arender = sync_to_async(_render)
arender_to_string = sync_to_async(_render_to_string)


def annotate_running(qs):
    running = Run.objects.filter(
        task=OuterRef("pk"), status__in=[RunStatus.PENDING, RunStatus.RUNNING]
    )
    return qs.annotate(is_running=Exists(running))


def mask_secret(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if len(v) <= 8:
        return "•" * len(v)
    return f"{v[:4]}{'•' * 6}{v[-4:]}"
