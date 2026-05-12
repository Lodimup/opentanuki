from django import forms

from .models import ScheduleType, Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "name",
            "prompt",
            "working_dir",
            "model",
            "permission_mode",
            "allowed_tools",
            "disallowed_tools",
            "add_dirs",
            "output_format",
            "dangerously_skip_permissions",
            "verbose",
            "max_budget_usd",
            "extra_args",
            "schedule_type",
            "interval_seconds",
            "cron_expr",
            "enabled",
            "continue_conversation",
            "claude_session_id",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "brut-input", "placeholder": "Daily code review"}),
            "prompt": forms.Textarea(attrs={"class": "brut-input", "rows": 4, "placeholder": "Review this morning's commits and summarize…"}),
            "working_dir": forms.TextInput(attrs={"class": "brut-input", "placeholder": "/Users/you/Projects/foo", "id": "id_working_dir"}),
            "model": forms.Select(
                attrs={"class": "brut-input"},
                choices=[
                    ("sonnet", "sonnet (recommended)"),
                    ("haiku", "haiku (fastest)"),
                    ("opus", "opus (smartest)"),
                ],
            ),
            "permission_mode": forms.Select(
                attrs={"class": "brut-input"},
                choices=[
                    ("", "—"),
                    ("default", "default"),
                    ("auto", "auto"),
                    ("acceptEdits", "acceptEdits"),
                    ("plan", "plan"),
                    ("bypassPermissions", "bypassPermissions"),
                    ("dontAsk", "dontAsk"),
                ],
            ),
            "allowed_tools": forms.TextInput(attrs={"class": "brut-input", "placeholder": "Bash(git *) Edit Read"}),
            "disallowed_tools": forms.TextInput(attrs={"class": "brut-input", "placeholder": "WebFetch"}),
            "add_dirs": forms.Textarea(attrs={"class": "brut-input", "rows": 2, "placeholder": "/path/one\n/path/two"}),
            "output_format": forms.Select(
                attrs={"class": "brut-input"},
                choices=[
                    ("stream-json", "stream-json (live)"),
                    ("text", "text"),
                    ("json", "json"),
                ],
            ),
            "max_budget_usd": forms.TextInput(attrs={"class": "brut-input", "placeholder": "5.00"}),
            "extra_args": forms.Textarea(attrs={"class": "brut-input", "rows": 3, "placeholder": "--effort\nhigh"}),
            "schedule_type": forms.Select(attrs={"class": "brut-input"}),
            "interval_seconds": forms.NumberInput(attrs={"class": "brut-input", "placeholder": "3600"}),
            "cron_expr": forms.TextInput(attrs={"class": "brut-input", "placeholder": "0 9 * * *"}),
            "claude_session_id": forms.TextInput(attrs={"class": "brut-input font-mono", "placeholder": "auto-generated on first run"}),
        }

    def clean(self):
        data = super().clean()
        st = data.get("schedule_type")
        if st == ScheduleType.INTERVAL and not data.get("interval_seconds"):
            self.add_error("interval_seconds", "Required for interval schedule.")
        if st == ScheduleType.CRON:
            expr = (data.get("cron_expr") or "").strip()
            if not expr:
                self.add_error("cron_expr", "Required for cron schedule.")
            else:
                parts = expr.split()
                if len(parts) != 5:
                    self.add_error("cron_expr", "Cron must have 5 fields (m h dom mon dow).")
                else:
                    try:
                        from croniter import croniter
                        croniter(expr)
                    except Exception as e:
                        self.add_error("cron_expr", f"Invalid cron: {e}")
        return data
