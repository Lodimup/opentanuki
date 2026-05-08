from uuid import UUID

from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from ninja import Schema

from ...models import RunStatus, Task
from ._router import router


class TaskRunsData(Schema):
    is_running: bool
    rows_html: str
    has_runs: bool


@router.get("/{task_id}/runs", response=TaskRunsData)
def get_runs(request, task_id: UUID):
    task = get_object_or_404(Task, pk=task_id, user=request.user)
    runs = list(task.runs.all()[:50])
    is_running = any(
        r.status in (RunStatus.PENDING, RunStatus.RUNNING) for r in runs
    )
    html = render_to_string(
        "scheduler/_task_runs_rows.html", {"runs": runs}, request=request
    )
    return {"is_running": is_running, "rows_html": html, "has_runs": bool(runs)}
