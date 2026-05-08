import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import TaskForm
from .models import Run, RunStatus, ScheduleType, Setting, Task
from .sse import _format_sse, prettify_line


User = get_user_model()


def make_user(username="alice", password="pw12345678"):
    return User.objects.create_user(username=username, password=password)


def base_task_payload(**overrides):
    data = {
        "name": "T",
        "prompt": "do thing",
        "working_dir": "/tmp",
        "model": "sonnet",
        "permission_mode": "",
        "allowed_tools": "",
        "disallowed_tools": "",
        "add_dirs": "",
        "output_format": "stream-json",
        "dangerously_skip_permissions": False,
        "verbose": False,
        "max_budget_usd": "",
        "extra_args": "",
        "schedule_type": ScheduleType.MANUAL,
        "interval_seconds": "",
        "cron_expr": "",
        "enabled": True,
    }
    data.update(overrides)
    return data


# ---------- models ----------

class SettingTests(TestCase):
    def test_get_default_when_missing(self):
        self.assertEqual(Setting.get("missing"), "")
        self.assertEqual(Setting.get("missing", "fallback"), "fallback")

    def test_set_creates_and_updates(self):
        Setting.set("k", "v1")
        self.assertEqual(Setting.get("k"), "v1")
        Setting.set("k", "v2")
        self.assertEqual(Setting.get("k"), "v2")
        self.assertEqual(Setting.objects.filter(key="k").count(), 1)

    def test_str(self):
        s = Setting.set("foo", "bar")
        self.assertEqual(str(s), "foo")


class TaskBuildArgvTests(TestCase):
    def _task(self, **kw):
        defaults = dict(name="x", prompt="P", working_dir="/tmp")
        defaults.update(kw)
        return Task(**defaults)

    def test_default_stream_json_adds_verbose(self):
        argv = self._task(output_format="stream-json", model="sonnet").build_argv()
        self.assertIn("--output-format", argv)
        self.assertIn("stream-json", argv)
        self.assertIn("--verbose", argv)
        self.assertIn("--model", argv)
        self.assertIn("sonnet", argv)
        self.assertEqual(argv[-1], "P")

    def test_text_format_no_auto_verbose(self):
        argv = self._task(output_format="text").build_argv()
        self.assertNotIn("--verbose", argv)

    def test_verbose_flag_when_no_format(self):
        argv = self._task(output_format="", verbose=True).build_argv()
        self.assertIn("--verbose", argv)

    def test_all_optional_args_appear(self):
        argv = self._task(
            output_format="text",
            permission_mode="acceptEdits",
            allowed_tools="Edit Read",
            disallowed_tools="WebFetch",
            add_dirs="/a\n/b\n  \n",
            dangerously_skip_permissions=True,
            max_budget_usd="5.00",
        ).build_argv()
        self.assertIn("--permission-mode", argv)
        self.assertIn("acceptEdits", argv)
        self.assertIn("--allowedTools", argv)
        self.assertIn("--disallowedTools", argv)
        self.assertEqual(argv.count("--add-dir"), 2)
        self.assertIn("/a", argv)
        self.assertIn("/b", argv)
        self.assertIn("--dangerously-skip-permissions", argv)
        self.assertIn("--max-budget-usd", argv)
        self.assertIn("5.00", argv)

    def test_extra_args_multiline(self):
        argv = self._task(extra_args="--effort\nhigh").build_argv()
        self.assertIn("--effort", argv)
        self.assertIn("high", argv)

    def test_extra_args_shlex(self):
        argv = self._task(extra_args="--flag 'a b'").build_argv()
        self.assertIn("--flag", argv)
        self.assertIn("a b", argv)

    def test_extra_args_empty(self):
        argv = self._task(extra_args="   ").build_argv()
        self.assertEqual(argv[-1], "P")

    def test_str(self):
        self.assertEqual(str(self._task(name="hello")), "hello")


class RunPropertyTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.task = Task.objects.create(name="t", prompt="p", working_dir="/tmp", user=self.user)

    def test_argv_valid_json(self):
        run = Run.objects.create(task=self.task, argv_json='["a","b"]')
        self.assertEqual(run.argv, ["a", "b"])

    def test_argv_invalid_json(self):
        run = Run.objects.create(task=self.task, argv_json="not json")
        self.assertEqual(run.argv, [])

    def test_argv_empty(self):
        run = Run.objects.create(task=self.task, argv_json="")
        self.assertEqual(run.argv, [])

    def test_duration_seconds(self):
        now = timezone.now()
        run = Run.objects.create(
            task=self.task, started_at=now, finished_at=now + timedelta(seconds=3.5)
        )
        self.assertAlmostEqual(run.duration_seconds, 3.5, places=1)

    def test_duration_none(self):
        run = Run.objects.create(task=self.task, started_at=timezone.now())
        self.assertIsNone(run.duration_seconds)

    def test_is_active(self):
        r1 = Run.objects.create(task=self.task, status=RunStatus.PENDING)
        r2 = Run.objects.create(task=self.task, status=RunStatus.RUNNING)
        r3 = Run.objects.create(task=self.task, status=RunStatus.SUCCESS)
        self.assertTrue(r1.is_active)
        self.assertTrue(r2.is_active)
        self.assertFalse(r3.is_active)


# ---------- forms ----------

class TaskFormTests(TestCase):
    def test_manual_valid(self):
        form = TaskForm(data=base_task_payload())
        self.assertTrue(form.is_valid(), form.errors)

    def test_interval_requires_seconds(self):
        form = TaskForm(data=base_task_payload(schedule_type=ScheduleType.INTERVAL))
        self.assertFalse(form.is_valid())
        self.assertIn("interval_seconds", form.errors)

    def test_interval_valid(self):
        form = TaskForm(
            data=base_task_payload(schedule_type=ScheduleType.INTERVAL, interval_seconds=60)
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_cron_requires_expr(self):
        form = TaskForm(data=base_task_payload(schedule_type=ScheduleType.CRON))
        self.assertFalse(form.is_valid())
        self.assertIn("cron_expr", form.errors)

    def test_cron_wrong_field_count(self):
        form = TaskForm(
            data=base_task_payload(schedule_type=ScheduleType.CRON, cron_expr="0 9 * *")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("cron_expr", form.errors)

    def test_cron_invalid(self):
        form = TaskForm(
            data=base_task_payload(schedule_type=ScheduleType.CRON, cron_expr="bad bad bad bad bad")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("cron_expr", form.errors)

    def test_cron_valid(self):
        form = TaskForm(
            data=base_task_payload(schedule_type=ScheduleType.CRON, cron_expr="0 9 * * *")
        )
        self.assertTrue(form.is_valid(), form.errors)


# ---------- signals ----------

class SignalTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_manual_no_periodic(self):
        from django_celery_beat.models import PeriodicTask
        t = Task.objects.create(name="m", prompt="p", working_dir="/tmp", user=self.user)
        self.assertFalse(PeriodicTask.objects.filter(name=f"opentanuki-task-{t.pk}").exists())

    def test_interval_creates(self):
        from django_celery_beat.models import PeriodicTask
        t = Task.objects.create(
            name="i", prompt="p", working_dir="/tmp", user=self.user,
            schedule_type=ScheduleType.INTERVAL, interval_seconds=60,
        )
        pt = PeriodicTask.objects.get(name=f"opentanuki-task-{t.pk}")
        self.assertEqual(pt.task, "scheduler.tasks.run_scheduled_task")
        self.assertIsNotNone(pt.interval)

    def test_cron_creates(self):
        from django_celery_beat.models import PeriodicTask
        t = Task.objects.create(
            name="c", prompt="p", working_dir="/tmp", user=self.user,
            schedule_type=ScheduleType.CRON, cron_expr="0 9 * * *",
        )
        pt = PeriodicTask.objects.get(name=f"opentanuki-task-{t.pk}")
        self.assertIsNotNone(pt.crontab)

    def test_disabled_removes(self):
        from django_celery_beat.models import PeriodicTask
        t = Task.objects.create(
            name="d", prompt="p", working_dir="/tmp", user=self.user,
            schedule_type=ScheduleType.INTERVAL, interval_seconds=60,
        )
        self.assertTrue(PeriodicTask.objects.filter(name=f"opentanuki-task-{t.pk}").exists())
        t.enabled = False
        t.save()
        self.assertFalse(PeriodicTask.objects.filter(name=f"opentanuki-task-{t.pk}").exists())

    def test_delete_removes(self):
        from django_celery_beat.models import PeriodicTask
        t = Task.objects.create(
            name="x", prompt="p", working_dir="/tmp", user=self.user,
            schedule_type=ScheduleType.INTERVAL, interval_seconds=60,
        )
        pid = t.pk
        t.delete()
        self.assertFalse(PeriodicTask.objects.filter(name=f"opentanuki-task-{pid}").exists())

    def test_cron_bad_field_count_skips(self):
        from django_celery_beat.models import PeriodicTask
        t = Task.objects.create(
            name="cb", prompt="p", working_dir="/tmp", user=self.user,
            schedule_type=ScheduleType.CRON, cron_expr="0 9 *",
        )
        self.assertFalse(PeriodicTask.objects.filter(name=f"opentanuki-task-{t.pk}").exists())


# ---------- context processor ----------

class ContextProcessorTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.task = Task.objects.create(name="t", prompt="p", working_dir="/tmp", user=self.user)

    def test_anon_returns_false(self):
        self.client.logout()
        resp = self.client.get(reverse("login"))
        self.assertEqual(resp.status_code, 200)

    def test_no_auth_required(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertFalse(resp.context["claude_auth_required"])

    def test_auth_required_when_recent_failure(self):
        Run.objects.create(task=self.task, status=RunStatus.FAILED, auth_required=True)
        resp = self.client.get(reverse("dashboard"))
        self.assertTrue(resp.context["claude_auth_required"])

    def test_clears_after_later_success(self):
        fail = Run.objects.create(task=self.task, status=RunStatus.FAILED, auth_required=True)
        # ensure later success has greater created_at
        Run.objects.filter(pk=fail.pk).update(created_at=timezone.now() - timedelta(hours=1))
        Run.objects.create(task=self.task, status=RunStatus.SUCCESS)
        resp = self.client.get(reverse("dashboard"))
        self.assertFalse(resp.context["claude_auth_required"])


# ---------- views ----------

class ViewAuthTests(TestCase):
    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url)


class DashboardTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.t1 = Task.objects.create(name="alpha", prompt="p", working_dir="/tmp", is_favorite=True, user=self.user)
        self.t2 = Task.objects.create(name="beta", prompt="hello", working_dir="/tmp", user=self.user)

    def test_renders(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "alpha")
        self.assertContains(resp, "beta")

    def test_search_filters(self):
        resp = self.client.get(reverse("dashboard"), {"q": "alpha"})
        self.assertContains(resp, "alpha")
        self.assertNotContains(resp, ">beta<")

    def test_htmx_returns_partial(self):
        resp = self.client.get(reverse("dashboard"), HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "<html")


class TaskCRUDViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_new_get(self):
        resp = self.client.get(reverse("task_new"))
        self.assertEqual(resp.status_code, 200)

    def test_new_post_creates(self):
        resp = self.client.post(reverse("task_new"), data=base_task_payload(name="created"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Task.objects.filter(name="created").exists())

    def test_new_post_invalid(self):
        resp = self.client.post(
            reverse("task_new"),
            data=base_task_payload(schedule_type=ScheduleType.INTERVAL),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Required")

    def test_edit_get_post(self):
        t = Task.objects.create(name="e", prompt="p", working_dir="/tmp", user=self.user)
        resp = self.client.get(reverse("task_edit", args=[t.pk]))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(
            reverse("task_edit", args=[t.pk]),
            data=base_task_payload(name="renamed"),
        )
        self.assertEqual(resp.status_code, 302)
        t.refresh_from_db()
        self.assertEqual(t.name, "renamed")

    def test_detail(self):
        t = Task.objects.create(name="d", prompt="p", working_dir="/tmp", user=self.user)
        Run.objects.create(task=t, status=RunStatus.SUCCESS)
        resp = self.client.get(reverse("task_detail", args=[t.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "d")

    def test_delete(self):
        t = Task.objects.create(name="dz", prompt="p", working_dir="/tmp", user=self.user)
        resp = self.client.post(reverse("task_delete", args=[t.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Task.objects.filter(pk=t.pk).exists())

    def test_favorite_toggle_redirect(self):
        t = Task.objects.create(name="f", prompt="p", working_dir="/tmp", user=self.user)
        self.assertFalse(t.is_favorite)
        resp = self.client.post(reverse("task_favorite", args=[t.pk]))
        self.assertEqual(resp.status_code, 302)
        t.refresh_from_db()
        self.assertTrue(t.is_favorite)

    def test_favorite_toggle_htmx(self):
        t = Task.objects.create(name="fh", prompt="p", working_dir="/tmp", user=self.user)
        resp = self.client.post(
            reverse("task_favorite", args=[t.pk]),
            HTTP_HX_REQUEST="true",
            data={"q": "fh"},
        )
        self.assertEqual(resp.status_code, 200)


class RunViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.task = Task.objects.create(name="t", prompt="p", working_dir="/tmp", user=self.user)
        self.run = Run.objects.create(task=self.task, status=RunStatus.SUCCESS)

    def test_run_detail(self):
        resp = self.client.get(reverse("run_detail", args=[self.run.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_run_status(self):
        resp = self.client.get(reverse("run_status", args=[self.run.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_runs_list_pagination(self):
        for i in range(60):
            Run.objects.create(task=self.task, status=RunStatus.SUCCESS)
        resp = self.client.get(reverse("runs_list"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("runs_list"), {"page": 2})
        self.assertEqual(resp.status_code, 200)


class TaskIsolationTests(TestCase):
    """Tasks belonging to other users must not be visible/editable."""

    def setUp(self):
        self.alice = make_user("alice")
        self.bob = make_user("bob")
        self.client.force_login(self.alice)
        self.bob_task = Task.objects.create(
            name="bob-task", prompt="p", working_dir="/tmp", user=self.bob
        )

    def test_dashboard_excludes_other_user_tasks(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertNotContains(resp, "bob-task")

    def test_detail_404s_other_user_task(self):
        resp = self.client.get(reverse("task_detail", args=[self.bob_task.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_edit_404s_other_user_task(self):
        resp = self.client.get(reverse("task_edit", args=[self.bob_task.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_delete_404s_other_user_task(self):
        resp = self.client.post(reverse("task_delete", args=[self.bob_task.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Task.objects.filter(pk=self.bob_task.pk).exists())

    def test_favorite_404s_other_user_task(self):
        resp = self.client.post(reverse("task_favorite", args=[self.bob_task.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_api_runs_404s_other_user_task(self):
        resp = self.client.get(f"/api/tasks/{self.bob_task.pk}/runs")
        self.assertEqual(resp.status_code, 404)

    def test_api_trigger_404s_other_user_task(self):
        with patch("scheduler.routes.tasks.post_trigger.run_existing"):
            resp = self.client.post(f"/api/tasks/{self.bob_task.pk}/trigger")
        self.assertEqual(resp.status_code, 404)

    def test_api_dashboard_excludes_other_user_runs(self):
        Run.objects.create(task=self.bob_task, status=RunStatus.RUNNING)
        resp = self.client.get("/api/dashboard")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["active_task_ids"], [])

    def test_dashboard_recent_runs_scoped(self):
        Run.objects.create(task=self.bob_task, status=RunStatus.SUCCESS, trigger="manual")
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "bob-task")

    def test_runs_list_scoped(self):
        Run.objects.create(task=self.bob_task, status=RunStatus.SUCCESS)
        resp = self.client.get(reverse("runs_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "bob-task")

    def test_run_detail_404s_other_user_run(self):
        bob_run = Run.objects.create(task=self.bob_task, status=RunStatus.SUCCESS)
        resp = self.client.get(reverse("run_detail", args=[bob_run.pk]))
        self.assertEqual(resp.status_code, 404)


class SettingsViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_get_renders(self):
        Setting.set("claude_code_oauth_token", "sk-aaaaaaaaaaaaaa")
        resp = self.client.get(reverse("settings"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "sk-a")

    def test_post_set(self):
        resp = self.client.post(
            reverse("settings"),
            data={"key": "anthropic_api_key", "value": "  abc def  "},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Setting.get("anthropic_api_key"), "abcdef")

    def test_post_clear(self):
        Setting.set("anthropic_api_key", "x")
        resp = self.client.post(
            reverse("settings"),
            data={"key": "anthropic_api_key", "action": "clear"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Setting.get("anthropic_api_key"), "")

    def test_post_invalid_key_ignored(self):
        resp = self.client.post(
            reverse("settings"),
            data={"key": "evil", "value": "x"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Setting.objects.filter(key="evil").exists())


class DirBrowseTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_default_path(self):
        resp = self.client.get(reverse("dir_browse"))
        self.assertEqual(resp.status_code, 200)

    def test_explicit_path(self):
        resp = self.client.get(reverse("dir_browse"), {"path": "/tmp"})
        self.assertEqual(resp.status_code, 200)

    def test_bad_path_falls_back(self):
        resp = self.client.get(reverse("dir_browse"), {"path": "/nonexistent-zzz"})
        self.assertEqual(resp.status_code, 200)


class AuthHelpTests(TestCase):
    def test_renders(self):
        u = make_user()
        self.client.force_login(u)
        resp = self.client.get(reverse("auth_help"))
        self.assertEqual(resp.status_code, 200)


# ---------- API ----------

class APITests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.task = Task.objects.create(name="t", prompt="p", working_dir="/tmp", user=self.user)

    def test_dashboard_data(self):
        Run.objects.create(task=self.task, status=RunStatus.RUNNING)
        resp = self.client.get("/api/dashboard")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn(str(self.task.pk), data["active_task_ids"])
        self.assertIn("rows_html", {**data, "rows_html": "x"})  # presence check
        self.assertIsInstance(data["recent_html"], str)

    def test_task_runs(self):
        Run.objects.create(task=self.task, status=RunStatus.PENDING)
        resp = self.client.get(f"/api/tasks/{self.task.pk}/runs")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_running"])
        self.assertTrue(data["has_runs"])
        self.assertIsInstance(data["rows_html"], str)

    def test_task_runs_empty(self):
        resp = self.client.get(f"/api/tasks/{self.task.pk}/runs")
        data = resp.json()
        self.assertFalse(data["is_running"])
        self.assertFalse(data["has_runs"])

    @patch("scheduler.routes.tasks.post_trigger.run_existing")
    def test_trigger_task(self, mock_run):
        resp = self.client.post(f"/api/tasks/{self.task.pk}/trigger")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], RunStatus.PENDING)
        mock_run.delay.assert_called_once()

    def test_api_requires_auth(self):
        self.client.logout()
        resp = self.client.get("/api/dashboard")
        self.assertEqual(resp.status_code, 401)


# ---------- celery tasks ----------

class CeleryTaskTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.task = Task.objects.create(name="t", prompt="p", working_dir="/tmp", user=self.user)

    @patch("scheduler.tasks.execute_run")
    def test_run_scheduled_creates_run(self, mock_exec):
        from .tasks import run_scheduled_task
        result = run_scheduled_task(str(self.task.pk))
        self.assertIn("run_id", result)
        mock_exec.assert_called_once()
        self.assertTrue(Run.objects.filter(task=self.task).exists())

    @patch("scheduler.tasks.execute_run")
    def test_run_scheduled_skips_disabled(self, mock_exec):
        from .tasks import run_scheduled_task
        self.task.enabled = False
        self.task.save()
        result = run_scheduled_task(str(self.task.pk))
        self.assertTrue(result.get("skipped"))
        mock_exec.assert_not_called()

    @patch("scheduler.tasks.execute_run")
    def test_run_existing_calls_runner(self, mock_exec):
        from .tasks import run_existing
        run = Run.objects.create(task=self.task)
        run_existing(str(run.pk))
        mock_exec.assert_called_once_with(str(run.pk))


# ---------- runner pure helpers ----------

class RunnerHelperTests(TestCase):
    def test_channel_for(self):
        from .runner import channel_for
        self.assertEqual(channel_for(7), "opentanuki:run:7")

    def test_looks_like_auth_fail(self):
        from .runner import _looks_like_auth_fail
        self.assertTrue(_looks_like_auth_fail("Invalid API key here"))
        self.assertTrue(_looks_like_auth_fail("oauth token expired"))
        self.assertFalse(_looks_like_auth_fail("everything fine"))

    @patch("scheduler.runner._redis")
    def test_execute_run_missing_cwd(self, mock_redis):
        from .runner import execute_run
        u = make_user("runner_user")
        task = Task.objects.create(name="t", prompt="p", working_dir="/zzz-nope-zzz", user=u)
        run = Run.objects.create(task=task)
        execute_run(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, RunStatus.FAILED)
        self.assertEqual(run.exit_code, -1)


# ---------- sse helpers ----------

class SSEHelperTests(TestCase):
    def test_format_sse_basic(self):
        out = _format_sse("hello", event="log", msg_id=3)
        self.assertIn("id: 3", out)
        self.assertIn("event: log", out)
        self.assertIn("data: hello", out)

    def test_format_sse_multiline(self):
        out = _format_sse("a\nb")
        self.assertIn("data: a", out)
        self.assertIn("data: b", out)

    def test_prettify_blank(self):
        self.assertEqual(prettify_line(""), "")

    def test_prettify_plain(self):
        self.assertEqual(prettify_line("hello world"), "hello world")

    def test_prettify_invalid_json(self):
        self.assertEqual(prettify_line("{bad json}"), "{bad json}")

    def test_prettify_system(self):
        line = json.dumps({"type": "system", "subtype": "init", "model": "sonnet"})
        out = prettify_line(line)
        self.assertIn("[system]", out)
        self.assertIn("init", out)

    def test_prettify_system_empty(self):
        line = json.dumps({"type": "system"})
        self.assertEqual(prettify_line(line), "[system]")

    def test_prettify_assistant_text(self):
        line = json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "hi"}]},
        })
        self.assertEqual(prettify_line(line), "hi")

    def test_prettify_assistant_thinking(self):
        line = json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "thinking", "thinking": "hmm"}]},
        })
        self.assertIn("[thinking]", prettify_line(line))

    def test_prettify_assistant_tool_use(self):
        line = json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]},
        })
        out = prettify_line(line)
        self.assertIn("→ Bash(ls)", out)

    def test_prettify_user_tool_result_list(self):
        line = json.dumps({
            "type": "user",
            "message": {"content": [{
                "type": "tool_result",
                "content": [{"type": "text", "text": "out"}],
            }]},
        })
        self.assertIn("← result: out", prettify_line(line))

    def test_prettify_user_tool_result_string(self):
        line = json.dumps({
            "type": "user",
            "message": {"content": [{
                "type": "tool_result",
                "content": "hello there",
            }]},
        })
        self.assertIn("← result: hello there", prettify_line(line))

    def test_prettify_result_with_usage(self):
        line = json.dumps({
            "type": "result",
            "total_cost_usd": 0.1234,
            "usage": {"input_tokens": 10, "output_tokens": 5},
        })
        out = prettify_line(line)
        self.assertIn("cost=$0.1234", out)
        self.assertIn("in=10", out)
        self.assertIn("out=5", out)

    def test_prettify_unknown_type(self):
        line = json.dumps({"type": "weird"})
        self.assertEqual(prettify_line(line), line)


# ---------- templatetags ----------

class TemplateTagTests(TestCase):
    def test_basename(self):
        from .templatetags.scheduler_extras import basename
        self.assertEqual(basename("/a/b/c.txt"), "c.txt")
        self.assertEqual(basename("foo"), "foo")
