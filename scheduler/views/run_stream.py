from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from ..models import Run
from ..sse import sse_response


@login_required
@require_GET
def run_stream(request, pk):
    get_object_or_404(Run, pk=pk, task__user=request.user)
    last = request.headers.get("Last-Event-ID") or request.GET.get("lastEventId") or "0"
    try:
        last_id = int(last)
    except (TypeError, ValueError):
        last_id = 0
    return sse_response(pk, last_event_id=last_id)
