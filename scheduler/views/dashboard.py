from django.contrib.auth.decorators import login_required
from django.db.models import Q

from ..models import Run, Task
from ._helpers import annotate_running, arender


@login_required
async def dashboard(request):
    q = (request.GET.get("q") or "").strip()
    user = await request.auser()
    qs = annotate_running(Task.objects.filter(user=user))
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(prompt__icontains=q) | Q(working_dir__icontains=q)
        )
    tasks = [t async for t in qs]
    favorites = sorted([t for t in tasks if t.is_favorite], key=lambda x: x.name.lower())
    others = [t for t in tasks if not t.is_favorite]
    if request.headers.get("HX-Request"):
        return await arender(
            request,
            "scheduler/_task_grid.html",
            {"favorites": favorites, "others": others, "q": q},
        )
    recent = [
        r
        async for r in Run.objects.select_related("task").filter(task__user=user)[:24]
    ]
    return await arender(
        request,
        "scheduler/dashboard.html",
        {"favorites": favorites, "others": others, "q": q, "recent": recent},
    )
