from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_searchtopic_schedule"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcescope",
            name="use_all_engines",
            field=models.BooleanField(default=True),
        ),
    ]
