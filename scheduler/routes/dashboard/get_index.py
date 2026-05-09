from uuid import UUID

from ninja import Schema

from ...models import Run, RunStatus
from ...views._helpers import arender_to_string
from ._router import router


class DashboardData(Schema):
    active_task_ids: list[UUID]
    recent_html: str


@router.get("", response=DashboardData)
async def get_dashboard(request):
    user = await request.auser()
    active = [
        tid
        async for tid in Run.objects.filter(
            status__in=[RunStatus.PENDING, RunStatus.RUNNING],
            task__user=user,
        )
        .values_list("task_id", flat=True)
        .distinct()
    ]
    recent = [
        r async for r in Run.objects.select_related("task").filter(task__user=user)[:24]
    ]
    html = await arender_to_string(
        "scheduler/_recent_runs_rows.html", {"recent": recent}, request=request
    )
    return {"active_task_ids": active, "recent_html": html}
