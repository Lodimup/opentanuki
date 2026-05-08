from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_GET

from ..models import Run


@login_required
@require_GET
def runs_list(request):
    qs = Run.objects.select_related("task").filter(task__user=request.user)
    page_num = request.GET.get("page") or 1
    paginator = Paginator(qs, 50)
    page = paginator.get_page(page_num)
    return render(request, "scheduler/runs.html", {"page": page, "recent": page.object_list})
