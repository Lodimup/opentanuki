from django.db.models import Exists, OuterRef

from ..models import Run, RunStatus

SETTING_KEYS = ("claude_code_oauth_token", "anthropic_api_key")


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
