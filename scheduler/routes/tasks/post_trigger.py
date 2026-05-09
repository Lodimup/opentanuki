from uuid import UUID

from django.shortcuts import aget_object_or_404
from ninja import Schema

from ...models import Run, RunStatus, Task
from ...tasks import run_existing
from ._router import router


class TriggerResponse(Schema):
    run_id: UUID
    status: str


@router.post("/{task_id}/trigger", response=TriggerResponse)
async def post_trigger(request, task_id: UUID):
    user = await request.auser()
    task = await aget_object_or_404(Task, pk=task_id, user=user)
    run = await Run.objects.acreate(task=task, status=RunStatus.PENDING, trigger="manual")
    run_existing.delay(str(run.pk))
    return {"run_id": run.pk, "status": run.status}
