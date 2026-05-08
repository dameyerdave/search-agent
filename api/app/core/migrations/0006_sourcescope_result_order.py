from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_user_owned_search_assets"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcescope",
            name="result_order",
            field=models.CharField(
                choices=[("relevance", "Relevance"), ("newest", "Time (newest first)")],
                default="relevance",
                max_length=16,
            ),
        ),
    ]
