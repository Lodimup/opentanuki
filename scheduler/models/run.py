import json

from django.db import models

from ._base import BaseAutoDate, BaseUUID
from .task import Task


class RunStatus(models.TextChoices):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"


class Run(BaseUUID, BaseAutoDate):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=20, choices=RunStatus.choices, default=RunStatus.PENDING)
    trigger = models.CharField(max_length=20, default="manual", help_text="manual | scheduled")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    pid = models.IntegerField(null=True, blank=True)
    argv_json = models.TextField(blank=True, default="[]")
    log_path = models.CharField(max_length=512, blank=True, default="")
    auth_required = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    @property
    def argv(self):
        try:
            return json.loads(self.argv_json or "[]")
        except json.JSONDecodeError:
            return []

    @property
    def duration_seconds(self):
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def is_active(self):
        return self.status in (RunStatus.PENDING, RunStatus.RUNNING)
