from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..models import Setting
from ._helpers import SETTING_KEYS, mask_secret


@login_required
def settings_view(request):
    if request.method == "POST":
        action = request.POST.get("action") or ""
        key = request.POST.get("key") or ""
        if key not in SETTING_KEYS:
            return redirect("settings")
        if action == "clear":
            Setting.objects.filter(key=key).delete()
        else:
            raw = request.POST.get("value") or ""
            value = "".join(raw.split())
            if value:
                Setting.set(key, value)
        return redirect("settings")
    values = {k: Setting.get(k, "") for k in SETTING_KEYS}
    masked = {k: mask_secret(v) for k, v in values.items()}
    return render(
        request,
        "scheduler/settings.html",
        {"masked": masked, "is_set": {k: bool(v) for k, v in values.items()}},
    )
