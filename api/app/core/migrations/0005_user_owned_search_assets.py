from django.conf import settings
from django.db import migrations, models
from django.utils.text import slugify


def _get_or_create_legacy_owner(apps):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    owner = User.objects.filter(is_superuser=True).order_by("id").first()
    if owner is None:
        owner = User.objects.order_by("id").first()
    if owner is not None:
        return owner

    base_username = "legacy-owner"
    username = base_username
    counter = 2
    while User.objects.filter(username=username).exists():
        username = f"{base_username}-{counter}"
        counter += 1

    owner = User.objects.create(
        username=username,
        email=f"{username}@example.invalid",
        is_active=False,
        password="!",
    )
    return owner


def assign_existing_assets_to_owner(apps, _schema_editor):
    SourceScope = apps.get_model("core", "SourceScope")
    SearchTopic = apps.get_model("core", "SearchTopic")

    owner = _get_or_create_legacy_owner(apps)
    SourceScope.objects.filter(owner__isnull=True).update(owner=owner)
    SearchTopic.objects.filter(owner__isnull=True).update(owner=owner)

    for topic in SearchTopic.objects.filter(slug="").order_by("id"):
        base_slug = slugify(topic.name) or "topic"
        candidate = base_slug
        counter = 2
        while SearchTopic.objects.exclude(pk=topic.pk).filter(
            owner=topic.owner, slug=candidate
        ).exists():
            candidate = f"{base_slug}-{counter}"
            counter += 1
        topic.slug = candidate
        topic.save(update_fields=["slug"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0004_sourcescope_use_all_categories"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcescope",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="source_scopes",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="searchtopic",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="search_topics",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="sourcescope",
            name="name",
            field=models.CharField(max_length=120),
        ),
        migrations.AlterField(
            model_name="searchtopic",
            name="name",
            field=models.CharField(max_length=180),
        ),
        migrations.AlterField(
            model_name="searchtopic",
            name="slug",
            field=models.SlugField(blank=True, max_length=200),
        ),
        migrations.RunPython(assign_existing_assets_to_owner, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="sourcescope",
            name="owner",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="source_scopes",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="searchtopic",
            name="owner",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="search_topics",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name="sourcescope",
            constraint=models.UniqueConstraint(
                fields=("owner", "name"),
                name="unique_source_scope_name_per_owner",
            ),
        ),
        migrations.AddConstraint(
            model_name="searchtopic",
            constraint=models.UniqueConstraint(
                fields=("owner", "name"),
                name="unique_search_topic_name_per_owner",
            ),
        ),
        migrations.AddConstraint(
            model_name="searchtopic",
            constraint=models.UniqueConstraint(
                fields=("owner", "slug"),
                name="unique_search_topic_slug_per_owner",
            ),
        ),
    ]
