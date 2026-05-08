from uuid import UUID

from django.template.loader import render_to_string
from ninja import Schema

from ...models import Run, RunStatus
from ._router import router


class DashboardData(Schema):
    active_task_ids: list[UUID]
    recent_html: str


@router.get("", response=DashboardData)
def get_dashboard(request):
    active = list(
        Run.objects.filter(
            status__in=[RunStatus.PENDING, RunStatus.RUNNING],
            task__user=request.user,
        )
        .values_list("task_id", flat=True)
        .distinct()
    )
    recent = list(
        Run.objects.select_related("task").filter(task__user=request.user)[:24]
    )
    html = render_to_string(
        "scheduler/_recent_runs_rows.html", {"recent": recent}, request=request
    )
    return {"active_task_ids": active, "recent_html": html}
