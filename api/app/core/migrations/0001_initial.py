from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SearchProviderConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(default="searxng", max_length=40, unique=True)),
                ("enabled", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SourceScope",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
                ("kind", models.CharField(choices=[("public", "Public"), ("research", "Research"), ("custom", "Custom")], default="public", max_length=32)),
                ("enabled", models.BooleanField(default=True)),
                ("searxng_categories", models.JSONField(blank=True, default=list)),
                ("searxng_engines", models.JSONField(blank=True, default=list)),
                ("language", models.CharField(blank=True, max_length=32)),
                ("safe_search", models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(2)])),
                ("time_range", models.CharField(choices=[("auto", "Auto"), ("any", "Any"), ("day", "Day"), ("month", "Month"), ("year", "Year")], default="auto", max_length=16)),
                ("max_results", models.PositiveSmallIntegerField(default=10, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(20)])),
                ("include_domains", models.JSONField(blank=True, default=list)),
                ("exclude_domains", models.JSONField(blank=True, default=list)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="SearchTopic",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=180, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=200, unique=True)),
                ("description", models.TextField(blank=True)),
                ("enabled", models.BooleanField(default=True)),
                ("queries", models.JSONField(blank=True, default=list)),
                ("required_terms", models.JSONField(blank=True, default=list)),
                ("excluded_terms", models.JSONField(blank=True, default=list)),
                ("lookback_days", models.PositiveSmallIntegerField(default=30, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(3650)])),
                ("max_results_per_query", models.PositiveSmallIntegerField(default=10, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(20)])),
                ("notes", models.TextField(blank=True)),
                ("last_checked_at", models.DateTimeField(blank=True, null=True)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_new_results_at", models.DateTimeField(blank=True, null=True)),
                ("last_run_status", models.CharField(choices=[("idle", "Idle"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("limited", "Limited")], default="idle", max_length=32)),
                ("source_scopes", models.ManyToManyField(blank=True, related_name="topics", to="core.sourcescope")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SearchRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("limited", "Limited")], default="running", max_length=32)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("source_scope_count", models.PositiveIntegerField(default=0)),
                ("request_count", models.PositiveIntegerField(default=0)),
                ("pages_crawled", models.PositiveIntegerField(default=0)),
                ("results_collected", models.PositiveIntegerField(default=0)),
                ("new_results_count", models.PositiveIntegerField(default=0)),
                ("query_snapshot", models.JSONField(blank=True, default=list)),
                ("error_message", models.TextField(blank=True)),
                ("topic", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="runs", to="core.searchtopic")),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="SearchResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=500)),
                ("url", models.URLField(max_length=1000)),
                ("normalized_url", models.CharField(max_length=1000)),
                ("domain", models.CharField(blank=True, max_length=255)),
                ("snippet", models.TextField(blank=True)),
                ("content", models.TextField(blank=True)),
                ("favicon_url", models.URLField(blank=True, max_length=1000)),
                ("score", models.FloatField(blank=True, null=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("matched_queries", models.JSONField(blank=True, default=list)),
                ("first_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("is_new", models.BooleanField(default=True)),
                ("raw_result", models.JSONField(blank=True, default=dict)),
                ("last_run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="results", to="core.searchrun")),
                ("source_scope", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="results", to="core.sourcescope")),
                ("topic", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="core.searchtopic")),
            ],
            options={"ordering": ["-is_new", "-published_at", "-first_seen_at"]},
        ),
        migrations.AddConstraint(
            model_name="searchresult",
            constraint=models.UniqueConstraint(fields=("topic", "normalized_url"), name="unique_result_per_topic_url"),
        ),
        migrations.AddIndex(
            model_name="searchresult",
            index=models.Index(fields=["topic", "is_new"], name="core_search_topic_i_47911b_idx"),
        ),
        migrations.AddIndex(
            model_name="searchresult",
            index=models.Index(fields=["domain"], name="core_search_domain_cad20a_idx"),
        ),
        migrations.AddIndex(
            model_name="searchresult",
            index=models.Index(fields=["published_at"], name="core_search_publish_8cdd22_idx"),
        ),
    ]
