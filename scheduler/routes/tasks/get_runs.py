from uuid import UUID

from django.shortcuts import aget_object_or_404
from ninja import Schema

from ...models import RunStatus, Task
from ...views._helpers import arender_to_string
from ._router import router


class TaskRunsData(Schema):
    is_running: bool
    rows_html: str
    has_runs: bool


@router.get("/{task_id}/runs", response=TaskRunsData)
async def get_runs(request, task_id: UUID):
    user = await request.auser()
    task = await aget_object_or_404(Task, pk=task_id, user=user)
    runs = [r async for r in task.runs.all()[:50]]
    is_running = any(
        r.status in (RunStatus.PENDING, RunStatus.RUNNING) for r in runs
    )
    html = await arender_to_string(
        "scheduler/_task_runs_rows.html", {"runs": runs}, request=request
    )
    return {"is_running": is_running, "rows_html": html, "has_runs": bool(runs)}
