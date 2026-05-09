from django.contrib.auth.decorators import login_required
from django.shortcuts import aget_object_or_404

from ..models import Run
from ._helpers import arender


@login_required
async def run_detail(request, pk):
    user = await request.auser()
    run = await aget_object_or_404(Run.objects.select_related("task"), pk=pk, task__user=user)
    return await arender(request, "scheduler/run_detail.html", {"run": run})
