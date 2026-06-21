from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_searchresult_is_saved_saved_title"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedFolder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=200)),
                ("sort_order", models.IntegerField(default=0)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="saved_folders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.AddConstraint(
            model_name="savedfolder",
            constraint=models.UniqueConstraint(fields=["owner", "name"], name="unique_folder_per_owner"),
        ),
        migrations.AddField(
            model_name="searchresult",
            name="folder",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="results",
                to="core.savedfolder",
            ),
        ),
    ]
