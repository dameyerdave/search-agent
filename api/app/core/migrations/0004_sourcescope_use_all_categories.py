from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_sourcescope_use_all_engines"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcescope",
            name="use_all_categories",
            field=models.BooleanField(default=True),
        ),
    ]
