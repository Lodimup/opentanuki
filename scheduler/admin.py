from django.contrib import admin
from .models import Run, Setting, Task


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("key", "updated_at")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("name", "schedule_type", "enabled", "updated_at")
    list_filter = ("schedule_type", "enabled")
    search_fields = ("name", "prompt")


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ("task", "status", "trigger", "started_at", "finished_at", "exit_code")
    list_filter = ("status", "trigger")
