from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from ..models import Task
from ._helpers import annotate_running


@login_required
def task_detail(request, pk):
    task = get_object_or_404(annotate_running(Task.objects.filter(user=request.user)), pk=pk)
    runs = task.runs.all()[:50]
    return render(request, "scheduler/task_detail.html", {"task": task, "runs": runs})
