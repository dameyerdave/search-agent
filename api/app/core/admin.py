from django.contrib import admin

from .models import SearchProviderConfig, SearchResult, SearchRun, SearchTopic, SourceScope


@admin.register(SourceScope)
class SourceScopeAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "enabled", "time_range", "max_results")
    list_filter = ("kind", "enabled", "time_range", "safe_search")
    search_fields = ("name", "description")


@admin.register(SearchTopic)
class SearchTopicAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "enabled",
        "schedule_every",
        "schedule_unit",
        "next_run_at",
        "lookback_days",
        "max_results_per_query",
        "last_run_status",
        "last_checked_at",
    )
    list_filter = ("enabled", "last_run_status")
    search_fields = ("name", "description", "slug")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("source_scopes",)


@admin.register(SearchProviderConfig)
class SearchProviderConfigAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "enabled",
        "updated_at",
    )


@admin.register(SearchRun)
class SearchRunAdmin(admin.ModelAdmin):
    list_display = (
        "topic",
        "status",
        "started_at",
        "completed_at",
        "request_count",
        "pages_crawled",
        "new_results_count",
    )
    list_filter = ("status", "topic")
    search_fields = ("topic__name", "error_message")


@admin.register(SearchResult)
class SearchResultAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "topic",
        "domain",
        "is_new",
        "published_at",
        "first_seen_at",
    )
    list_filter = ("topic", "source_scope", "is_new")
    search_fields = ("title", "url", "snippet", "domain")
