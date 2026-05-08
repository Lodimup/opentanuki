from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def auth_help(request):
    return render(request, "scheduler/auth_help.html")
