from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..forms import TaskForm


@login_required
def task_new(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            t.user = request.user
            t.save()
            return redirect("task_detail", pk=t.pk)
    else:
        form = TaskForm()
    return render(request, "scheduler/task_form.html", {"form": form, "task": None})
