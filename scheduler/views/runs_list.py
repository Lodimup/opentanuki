from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET

from ..models import Run
from ._helpers import arender


def _paginate(qs, page_num):
    paginator = Paginator(qs, 50)
    page = paginator.get_page(page_num)
    return page, list(page.object_list)


@login_required
@require_GET
async def runs_list(request):
    user = await request.auser()
    qs = Run.objects.select_related("task").filter(task__user=user)
    page_num = request.GET.get("page") or 1
    page, recent = await sync_to_async(_paginate)(qs, page_num)
    return await arender(request, "scheduler/runs.html", {"page": page, "recent": recent})
