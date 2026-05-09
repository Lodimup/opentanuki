from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import aget_object_or_404, redirect
from django.views.decorators.http import require_POST

from ..models import Task
from ._helpers import annotate_running, arender


@login_required
@require_POST
async def task_favorite(request, pk):
    user = await request.auser()
    task = await aget_object_or_404(Task, pk=pk, user=user)
    task.is_favorite = not task.is_favorite
    await task.asave(update_fields=["is_favorite", "updated_at"])
    if request.headers.get("HX-Request"):
        q = (request.POST.get("q") or request.GET.get("q") or "").strip()
        qs = annotate_running(Task.objects.filter(user=user))
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(prompt__icontains=q) | Q(working_dir__icontains=q)
            )
        tasks = [t async for t in qs]
        favorites = sorted([t for t in tasks if t.is_favorite], key=lambda x: x.name.lower())
        others = [t for t in tasks if not t.is_favorite]
        return await arender(
            request,
            "scheduler/_task_grid.html",
            {"favorites": favorites, "others": others, "q": q},
        )
    return redirect("dashboard")
