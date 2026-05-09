from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.shortcuts import aget_object_or_404, redirect

from ..forms import TaskForm
from ..models import Task
from ._helpers import arender


@login_required
async def task_edit(request, pk):
    user = await request.auser()
    task = await aget_object_or_404(Task, pk=pk, user=user)
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        is_valid = await sync_to_async(form.is_valid)()
        if is_valid:
            await sync_to_async(form.save)()
            return redirect("task_detail", pk=task.pk)
    else:
        form = TaskForm(instance=task)
    return await arender(request, "scheduler/task_form.html", {"form": form, "task": task})
