from django.contrib.auth.decorators import login_required

from ._helpers import arender


@login_required
async def auth_help(request):
    return await arender(request, "scheduler/auth_help.html")
