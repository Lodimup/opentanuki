from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Schema

from ...models import Run, RunStatus, Task
from ...tasks import run_existing
from ._router import router


class TriggerResponse(Schema):
    run_id: UUID
    status: str


@router.post("/{task_id}/trigger", response=TriggerResponse)
def post_trigger(request, task_id: UUID):
    task = get_object_or_404(Task, pk=task_id, user=request.user)
    run = Run.objects.create(task=task, status=RunStatus.PENDING, trigger="manual")
    run_existing.delay(str(run.pk))
    return {"run_id": run.pk, "status": run.status}
