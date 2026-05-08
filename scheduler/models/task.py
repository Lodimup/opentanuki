from django.conf import settings
from django.db import models

from ._base import BaseAutoDate, BaseUUID


class ScheduleType(models.TextChoices):
    MANUAL = "manual", "Manual only"
    INTERVAL = "interval", "Interval"
    CRON = "cron", "Cron"


class Task(BaseUUID, BaseAutoDate):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    name = models.CharField(max_length=200)
    prompt = models.TextField(help_text="Prompt passed to `claude -p <prompt>`.")
    working_dir = models.CharField(max_length=1024, help_text="Absolute path. claude runs in this cwd.")
    extra_args = models.TextField(
        blank=True,
        default="",
        help_text="Extra CLI args appended to claude. One arg per line OR shell-quoted single line.",
    )
    model = models.CharField(max_length=120, blank=True, default="sonnet")
    permission_mode = models.CharField(max_length=40, blank=True, default="")
    allowed_tools = models.CharField(max_length=500, blank=True, default="")
    disallowed_tools = models.CharField(max_length=500, blank=True, default="")
    add_dirs = models.TextField(blank=True, default="", help_text="One absolute path per line.")
    output_format = models.CharField(
        max_length=20,
        blank=True,
        default="stream-json",
        help_text="text, json, stream-json. Use stream-json for live UI streaming.",
    )
    dangerously_skip_permissions = models.BooleanField(default=False)
    verbose = models.BooleanField(default=False)
    max_budget_usd = models.CharField(max_length=20, blank=True, default="")

    schedule_type = models.CharField(
        max_length=20, choices=ScheduleType.choices, default=ScheduleType.MANUAL
    )
    interval_seconds = models.PositiveIntegerField(null=True, blank=True)
    cron_expr = models.CharField(max_length=200, blank=True, default="")

    enabled = models.BooleanField(default=True)
    is_favorite = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_favorite", "-updated_at"]

    def __str__(self):
        return self.name

    def build_argv(self) -> list[str]:
        argv = [settings.CLAUDE_BIN, "-p"]
        if self.output_format:
            argv += ["--output-format", self.output_format]
            if self.output_format in ("stream-json",):
                argv += ["--verbose"]
        elif self.verbose:
            argv += ["--verbose"]
        if self.model:
            argv += ["--model", self.model]
        if self.permission_mode:
            argv += ["--permission-mode", self.permission_mode]
        if self.allowed_tools.strip():
            argv += ["--allowedTools", self.allowed_tools.strip()]
        if self.disallowed_tools.strip():
            argv += ["--disallowedTools", self.disallowed_tools.strip()]
        for line in [l.strip() for l in self.add_dirs.splitlines() if l.strip()]:
            argv += ["--add-dir", line]
        if self.dangerously_skip_permissions:
            argv += ["--dangerously-skip-permissions"]
        if self.max_budget_usd:
            argv += ["--max-budget-usd", self.max_budget_usd]
        for tok in self._extra_arg_tokens():
            argv.append(tok)
        argv.append(self.prompt)
        return argv

    def _extra_arg_tokens(self) -> list[str]:
        raw = self.extra_args or ""
        if not raw.strip():
            return []
        if "\n" in raw:
            return [l.strip() for l in raw.splitlines() if l.strip()]
        import shlex
        return shlex.split(raw)
