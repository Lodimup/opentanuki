from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from ..models import Setting
from ._helpers import SETTING_KEYS, arender, mask_secret


@login_required
async def settings_view(request):
    if request.method == "POST":
        action = request.POST.get("action") or ""
        key = request.POST.get("key") or ""
        if key not in SETTING_KEYS:
            return redirect("settings")
        if action == "clear":
            await Setting.objects.filter(key=key).adelete()
        else:
            raw = request.POST.get("value") or ""
            value = "".join(raw.split())
            if value:
                await sync_to_async(Setting.set)(key, value)
        return redirect("settings")
    values = {k: await sync_to_async(Setting.get)(k, "") for k in SETTING_KEYS}
    masked = {k: mask_secret(v) for k, v in values.items()}
    return await arender(
        request,
        "scheduler/settings.html",
        {"masked": masked, "is_set": {k: bool(v) for k, v in values.items()}},
    )
