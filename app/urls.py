from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from scheduler.api import api as scheduler_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/", scheduler_api.urls),
    path("", include("scheduler.urls")),
]
