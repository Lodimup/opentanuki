from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from ..forms import TaskForm
from ._helpers import arender


def _save_form(form, user):
    t = form.save(commit=False)
    t.user = user
    t.save()
    return t


@login_required
async def task_new(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        is_valid = await sync_to_async(form.is_valid)()
        if is_valid:
            user = await request.auser()
            t = await sync_to_async(_save_form)(form, user)
            return redirect("task_detail", pk=t.pk)
    else:
        form = TaskForm()
    return await arender(request, "scheduler/task_form.html", {"form": form, "task": None})
