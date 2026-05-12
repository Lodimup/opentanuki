from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduler", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="continue_conversation",
            field=models.BooleanField(
                default=False,
                help_text="Resume the previous conversation each run via --resume <session_id>.",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="claude_session_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Session ID used by --resume. Auto-captured from last run; can be set manually.",
                max_length=64,
            ),
        ),
    ]
