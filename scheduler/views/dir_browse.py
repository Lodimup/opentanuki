import os
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET


@login_required
@require_GET
def dir_browse(request):
    """Server-side directory browser. Returns HTML fragment for htmx."""
    raw = request.GET.get("path") or os.path.expanduser("~")
    try:
        p = Path(raw).expanduser().resolve()
    except Exception:
        p = Path(os.path.expanduser("~"))
    if not p.is_dir():
        p = p.parent if p.parent.is_dir() else Path(os.path.expanduser("~"))

    try:
        entries = sorted(
            [e for e in p.iterdir() if e.is_dir() and not e.name.startswith(".")],
            key=lambda x: x.name.lower(),
        )
    except PermissionError:
        entries = []

    parent = p.parent if p.parent != p else None
    return render(
        request,
        "scheduler/_dir_browser.html",
        {"current": str(p), "parent": str(parent) if parent else "", "entries": entries},
    )
