from django.contrib.auth.decorators import login_required
from django.shortcuts import aget_object_or_404, redirect
from django.views.decorators.http import require_POST

from ..models import Task


@login_required
@require_POST
async def task_clear_session(request, pk):
    user = await request.auser()
    task = await aget_object_or_404(Task, pk=pk, user=user)
    task.claude_session_id = ""
    await task.asave(update_fields=["claude_session_id", "updated_at"])
    return redirect("task_detail", pk=task.pk)
