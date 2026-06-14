from django.db import migrations, models


def migrate_language_to_languages(apps, schema_editor):
    SourceScope = apps.get_model("core", "SourceScope")
    for scope in SourceScope.objects.exclude(language=""):
        scope.languages = [scope.language]
        scope.save(update_fields=["languages"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_cloudflareaccessidentity"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcescope",
            name="languages",
            field=models.JSONField(default=list, blank=True),
        ),
        migrations.RunPython(migrate_language_to_languages, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="sourcescope",
            name="language",
        ),
    ]
