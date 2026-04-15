from datetime import timedelta

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
from django.utils import timezone


def initialize_topic_schedule_defaults(apps, schema_editor):
    SearchTopic = apps.get_model("core", "SearchTopic")
    now = timezone.now()

    for topic in SearchTopic.objects.all():
        if topic.enabled:
            topic.next_run_at = now + timedelta(days=1)
        else:
            topic.next_run_at = None
        topic.save(update_fields=["next_run_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="searchtopic",
            name="schedule_every",
            field=models.PositiveIntegerField(
                default=1,
                validators=[MinValueValidator(1), MaxValueValidator(10000)],
            ),
        ),
        migrations.AddField(
            model_name="searchtopic",
            name="schedule_unit",
            field=models.CharField(
                choices=[
                    ("minutes", "Minutes"),
                    ("hours", "Hours"),
                    ("days", "Days"),
                    ("weeks", "Weeks"),
                ],
                default="days",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="searchtopic",
            name="next_run_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            initialize_topic_schedule_defaults,
            migrations.RunPython.noop,
        ),
    ]
