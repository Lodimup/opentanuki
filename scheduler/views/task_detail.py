from django.contrib.auth.decorators import login_required
from django.shortcuts import aget_object_or_404

from ..models import Task
from ._helpers import annotate_running, arender


@login_required
async def task_detail(request, pk):
    user = await request.auser()
    task = await aget_object_or_404(annotate_running(Task.objects.filter(user=user)), pk=pk)
    runs = [r async for r in task.runs.all()[:50]]
    return await arender(request, "scheduler/task_detail.html", {"task": task, "runs": runs})
