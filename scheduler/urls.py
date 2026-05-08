from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tasks/new/", views.task_new, name="task_new"),
    path("tasks/<uuid:pk>/", views.task_detail, name="task_detail"),
    path("tasks/<uuid:pk>/edit/", views.task_edit, name="task_edit"),
    path("tasks/<uuid:pk>/delete/", views.task_delete, name="task_delete"),
    path("tasks/<uuid:pk>/favorite/", views.task_favorite, name="task_favorite"),
    path("runs/", views.runs_list, name="runs_list"),
    path("runs/<uuid:pk>/", views.run_detail, name="run_detail"),
    path("runs/<uuid:pk>/stream/", views.run_stream, name="run_stream"),
    path("runs/<uuid:pk>/status/", views.run_status, name="run_status"),
    path("dir-browse/", views.dir_browse, name="dir_browse"),
    path("auth-help/", views.auth_help, name="auth_help"),
    path("settings/", views.settings_view, name="settings"),
]
