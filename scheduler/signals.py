"""Sync Task schedule changes to django-celery-beat PeriodicTask rows."""
import json

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import ScheduleType, Task


def _periodic_name(task: Task) -> str:
    return f"opentanuki-task-{task.pk}"


@receiver(post_save, sender=Task)
def sync_periodic(sender, instance: Task, raw=False, **kwargs):
    if raw:
        return
    from django_celery_beat.models import (
        CrontabSchedule,
        IntervalSchedule,
        PeriodicTask,
    )

    name = _periodic_name(instance)
    PeriodicTask.objects.filter(name=name).delete()
    if not instance.enabled or instance.schedule_type == ScheduleType.MANUAL:
        return

    kwargs_json = json.dumps({"task_id": str(instance.pk), "trigger": "scheduled"})
    if instance.schedule_type == ScheduleType.INTERVAL and instance.interval_seconds:
        sched, _ = IntervalSchedule.objects.get_or_create(
            every=instance.interval_seconds, period=IntervalSchedule.SECONDS
        )
        PeriodicTask.objects.create(
            name=name,
            task="scheduler.tasks.run_scheduled_task",
            interval=sched,
            kwargs=kwargs_json,
        )
    elif instance.schedule_type == ScheduleType.CRON and instance.cron_expr.strip():
        parts = instance.cron_expr.split()
        if len(parts) == 5:
            m, h, dom, mon, dow = parts
            sched, _ = CrontabSchedule.objects.get_or_create(
                minute=m, hour=h, day_of_month=dom, month_of_year=mon, day_of_week=dow,
                timezone="UTC",
            )
            PeriodicTask.objects.create(
                name=name,
                task="scheduler.tasks.run_scheduled_task",
                crontab=sched,
                kwargs=kwargs_json,
            )


@receiver(post_delete, sender=Task)
def remove_periodic(sender, instance: Task, **kwargs):
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(name=_periodic_name(instance)).delete()
