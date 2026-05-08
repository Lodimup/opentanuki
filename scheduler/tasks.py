from celery import shared_task

from .models import Run, RunStatus, Task
from .runner import execute_run


@shared_task(name="scheduler.tasks.run_scheduled_task")
def run_scheduled_task(task_id: str, trigger: str = "scheduled"):
    try:
        task = Task.objects.get(pk=task_id, enabled=True)
    except Task.DoesNotExist:
        return {"skipped": True, "reason": "task missing or disabled"}
    run = Run.objects.create(task=task, status=RunStatus.PENDING, trigger=trigger)
    execute_run(run.pk)
    return {"run_id": str(run.pk)}


@shared_task(name="scheduler.tasks.run_existing")
def run_existing(run_id: str):
    execute_run(run_id)
    return {"run_id": str(run_id)}
