from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from ..models import Run


@login_required
def run_detail(request, pk):
    run = get_object_or_404(Run.objects.select_related("task"), pk=pk, task__user=request.user)
    return render(request, "scheduler/run_detail.html", {"run": run})
