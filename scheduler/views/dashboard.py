from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from ..models import Run, Task
from ._helpers import annotate_running


@login_required
def dashboard(request):
    q = (request.GET.get("q") or "").strip()
    tasks = annotate_running(Task.objects.filter(user=request.user))
    if q:
        tasks = tasks.filter(
            Q(name__icontains=q) | Q(prompt__icontains=q) | Q(working_dir__icontains=q)
        )
    favorites = sorted([t for t in tasks if t.is_favorite], key=lambda x: x.name.lower())
    others = [t for t in tasks if not t.is_favorite]
    if request.headers.get("HX-Request"):
        return render(
            request,
            "scheduler/_task_grid.html",
            {"favorites": favorites, "others": others, "q": q},
        )
    recent = Run.objects.select_related("task").filter(task__user=request.user)[:24]
    return render(
        request,
        "scheduler/dashboard.html",
        {"favorites": favorites, "others": others, "q": q, "recent": recent},
    )
