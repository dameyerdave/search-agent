from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_sourcescope_languages"),
    ]

    operations = [
        migrations.AddField(
            model_name="searchresult",
            name="is_saved",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name="searchresult",
            name="saved_title",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
