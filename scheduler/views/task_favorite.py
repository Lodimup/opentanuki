from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import Task
from ._helpers import annotate_running


@login_required
@require_POST
def task_favorite(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.is_favorite = not task.is_favorite
    task.save(update_fields=["is_favorite", "updated_at"])
    if request.headers.get("HX-Request"):
        q = (request.POST.get("q") or request.GET.get("q") or "").strip()
        tasks = annotate_running(Task.objects.filter(user=request.user))
        if q:
            tasks = tasks.filter(
                Q(name__icontains=q) | Q(prompt__icontains=q) | Q(working_dir__icontains=q)
            )
        favorites = sorted([t for t in tasks if t.is_favorite], key=lambda x: x.name.lower())
        others = [t for t in tasks if not t.is_favorite]
        return render(
            request,
            "scheduler/_task_grid.html",
            {"favorites": favorites, "others": others, "q": q},
        )
    return redirect("dashboard")
