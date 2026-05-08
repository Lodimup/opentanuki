from .models import Run, RunStatus


def auth_status(request):
    """Expose `claude_auth_required` flag if any recent run flagged auth failure
    and no successful run since."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"claude_auth_required": False, "auth_failed_run": None}
    last_fail = (
        Run.objects.filter(auth_required=True, task__user=request.user)
        .order_by("-created_at")
        .first()
    )
    if not last_fail:
        return {"claude_auth_required": False, "auth_failed_run": None}
    later_success = Run.objects.filter(
        status=RunStatus.SUCCESS,
        task__user=request.user,
        created_at__gt=last_fail.created_at,
    ).exists()
    if later_success:
        return {"claude_auth_required": False, "auth_failed_run": None}
    return {"claude_auth_required": True, "auth_failed_run": last_fail}
