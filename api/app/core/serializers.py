from rest_framework import serializers

from .models import PushSubscription, SavedFolder, SearchProviderConfig, SearchResult, SearchRun, SearchTopic, SourceScope


class PushSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushSubscription
        fields = ("id", "endpoint", "p256dh", "auth", "created_at")
        read_only_fields = ("id", "created_at")


class SavedFolderSerializer(serializers.ModelSerializer):
    result_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = SavedFolder
        fields = ("id", "name", "sort_order", "result_count", "created_at", "updated_at")


def clean_string_list(value):
    if value is None:
        return []
    cleaned = []
    for item in value:
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return cleaned


class SourceScopeSerializer(serializers.ModelSerializer):
    searxng_categories = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
    )
    use_all_categories = serializers.BooleanField(required=False, default=True)
    use_all_engines = serializers.BooleanField(required=False, default=True)
    searxng_engines = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
    )
    include_domains = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
    )
    exclude_domains = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
    )
    languages = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
    )

    class Meta:
        model = SourceScope
        fields = (
            "id",
            "name",
            "description",
            "kind",
            "enabled",
            "searxng_categories",
            "use_all_categories",
            "use_all_engines",
            "searxng_engines",
            "languages",
            "safe_search",
            "time_range",
            "result_order",
            "max_results",
            "include_domains",
            "exclude_domains",
            "sort_order",
            "created_at",
            "updated_at",
        )

    def validate_searxng_categories(self, value):
        return clean_string_list(value)

    def validate_searxng_engines(self, value):
        from .services import load_searxng_engines, normalize_searxng_engines

        engines = normalize_searxng_engines(value)
        available_engines = set(load_searxng_engines())
        if available_engines:
            invalid = [engine for engine in engines if engine not in available_engines]
            if invalid:
                raise serializers.ValidationError(
                    "Choose engines from the available SearxNG engine list."
                )
        return engines

    def validate_include_domains(self, value):
        return clean_string_list(value)

    def validate_exclude_domains(self, value):
        return clean_string_list(value)

    def validate_languages(self, value):
        from .services import load_searxng_locales, normalize_searxng_languages

        languages = normalize_searxng_languages(value)

        locales = load_searxng_locales()
        if locales:
            invalid = [language for language in languages if language not in locales]
            if invalid:
                raise serializers.ValidationError(
                    "Choose languages from the available SearxNG language list."
                )
        return languages

    def validate(self, attrs):
        attrs = super().validate(attrs)
        use_all_categories = attrs.get("use_all_categories")
        if use_all_categories is None and self.instance is not None:
            use_all_categories = self.instance.use_all_categories

        categories = attrs.get("searxng_categories")
        if categories is None and self.instance is not None:
            categories = self.instance.searxng_categories

        if use_all_categories is False and not clean_string_list(categories or []):
            raise serializers.ValidationError(
                {"searxng_categories": "Add at least one category or switch to all categories."}
            )

        use_all_engines = attrs.get("use_all_engines")
        if use_all_engines is None and self.instance is not None:
            use_all_engines = self.instance.use_all_engines

        engines = attrs.get("searxng_engines")
        if engines is None and self.instance is not None:
            engines = self.instance.searxng_engines

        if use_all_engines is False and not clean_string_list(engines or []):
            raise serializers.ValidationError(
                {"searxng_engines": "Add at least one engine or switch to all available engines."}
            )
        return attrs


class SearchTopicSerializer(serializers.ModelSerializer):
    queries = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    required_terms = serializers.ListField(
        child=serializers.CharField(), allow_empty=True, required=False
    )
    excluded_terms = serializers.ListField(
        child=serializers.CharField(), allow_empty=True, required=False
    )
    source_scopes = SourceScopeSerializer(many=True, read_only=True)
    source_scope_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=SourceScope.objects.none(),
        source="source_scopes",
        write_only=True,
    )
    result_count = serializers.IntegerField(read_only=True)
    new_results_count = serializers.IntegerField(read_only=True)
    query_preview = serializers.SerializerMethodField()
    schedule_description = serializers.CharField(read_only=True)

    class Meta:
        model = SearchTopic
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "enabled",
            "queries",
            "required_terms",
            "excluded_terms",
            "lookback_days",
            "schedule_every",
            "schedule_unit",
            "max_results_per_query",
            "notes",
            "source_scopes",
            "source_scope_ids",
            "result_count",
            "new_results_count",
            "next_run_at",
            "last_checked_at",
            "last_success_at",
            "last_new_results_at",
            "last_run_status",
            "query_preview",
            "schedule_description",
            "created_at",
            "updated_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["source_scope_ids"].child_relation.queryset = (
                SourceScope.objects.filter(owner=request.user).order_by("sort_order", "name")
            )

    def validate_queries(self, value):
        cleaned = clean_string_list(value)
        if not cleaned:
            raise serializers.ValidationError("At least one search query is required.")
        return cleaned

    def validate_required_terms(self, value):
        return clean_string_list(value)

    def validate_excluded_terms(self, value):
        return clean_string_list(value)

    def get_query_preview(self, obj):
        required = clean_string_list(obj.required_terms)
        excluded = clean_string_list(obj.excluded_terms)
        preview = []
        for query in clean_string_list(obj.queries):
            parts = [query]
            parts.extend(required)
            parts.extend([f"-{term}" for term in excluded])
            preview.append(" ".join(parts))
        return preview


class SearchProviderConfigSerializer(serializers.ModelSerializer):
    searxng_base_url = serializers.SerializerMethodField()
    crawl4ai_enabled = serializers.SerializerMethodField()
    available_categories = serializers.SerializerMethodField()
    available_engines = serializers.SerializerMethodField()
    available_languages = serializers.SerializerMethodField()

    class Meta:
        model = SearchProviderConfig
        fields = (
            "id",
            "name",
            "enabled",
            "searxng_base_url",
            "crawl4ai_enabled",
            "available_categories",
            "available_engines",
            "available_languages",
            "created_at",
            "updated_at",
        )

    def get_searxng_base_url(self, _obj):
        from django.conf import settings

        return getattr(settings, "SEARXNG_BASE_URL", "")

    def get_crawl4ai_enabled(self, _obj):
        from django.conf import settings

        return getattr(settings, "CRAWL4AI_ENABLED", False)

    def get_available_categories(self, _obj):
        from .services import load_searxng_categories

        return load_searxng_categories()

    def get_available_engines(self, _obj):
        from .services import load_searxng_engines

        return load_searxng_engines()

    def get_available_languages(self, _obj):
        from .services import load_searxng_language_options

        return load_searxng_language_options()


class SearxNGSearchRequestSerializer(serializers.Serializer):
    q = serializers.CharField()
    categories = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
    )
    use_all_categories = serializers.BooleanField(required=False, default=True)
    use_all_engines = serializers.BooleanField(required=False, default=True)
    engines = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
    )
    languages = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
    )
    safesearch = serializers.IntegerField(required=False, min_value=0, max_value=2)
    time_range = serializers.CharField(required=False, allow_blank=True)
    result_order = serializers.ChoiceField(
        required=False,
        choices=SourceScope.ResultOrder.choices,
        default=SourceScope.ResultOrder.RELEVANCE,
    )
    pageno = serializers.IntegerField(required=False, min_value=1, default=1)
    max_results = serializers.IntegerField(required=False, min_value=1, max_value=50, default=10)
    include_domains = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
    )
    exclude_domains = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
    )
    extra_params = serializers.JSONField(required=False)

    def validate_categories(self, value):
        return clean_string_list(value)

    def validate_engines(self, value):
        from .services import load_searxng_engines, normalize_searxng_engines

        engines = normalize_searxng_engines(value)
        available_engines = set(load_searxng_engines())
        if available_engines:
            invalid = [engine for engine in engines if engine not in available_engines]
            if invalid:
                raise serializers.ValidationError(
                    "Choose engines from the available SearxNG engine list."
                )
        return engines

    def validate_include_domains(self, value):
        return clean_string_list(value)

    def validate_exclude_domains(self, value):
        return clean_string_list(value)

    def validate_time_range(self, value):
        allowed = {"", "day", "month", "year"}
        if value not in allowed:
            raise serializers.ValidationError("Use day, month, year, or leave blank.")
        return value

    def validate_languages(self, value):
        from .services import load_searxng_locales, normalize_searxng_languages

        languages = normalize_searxng_languages(value)

        locales = load_searxng_locales()
        if locales:
            invalid = [language for language in languages if language not in locales]
            if invalid:
                raise serializers.ValidationError(
                    "Choose languages from the available SearxNG language list."
                )
        return languages

    def validate_extra_params(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("extra_params must be a JSON object.")

        cleaned = {}
        for key, raw_value in value.items():
            clean_key = str(key).strip()
            if not clean_key or raw_value in (None, ""):
                continue
            cleaned[clean_key] = raw_value
        return cleaned

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get("use_all_categories", True) and not attrs.get("categories"):
            raise serializers.ValidationError(
                {"categories": "Add at least one category or search across all categories."}
            )
        if not attrs.get("use_all_engines", True) and not attrs.get("engines"):
            raise serializers.ValidationError(
                {"engines": "Add at least one engine or search across all available engines."}
            )
        return attrs


class SearchRunSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source="topic.name", read_only=True)

    class Meta:
        model = SearchRun
        fields = (
            "id",
            "topic",
            "topic_name",
            "status",
            "started_at",
            "completed_at",
            "source_scope_count",
            "request_count",
            "pages_crawled",
            "results_collected",
            "new_results_count",
            "query_snapshot",
            "error_message",
            "created_at",
            "updated_at",
        )


class SearchResultSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source="topic.name", read_only=True)
    source_scope_name = serializers.CharField(
        source="source_scope.name",
        read_only=True,
        allow_null=True,
    )
    folder_name = serializers.CharField(source="folder.name", read_only=True, allow_null=True)

    class Meta:
        model = SearchResult
        fields = (
            "id",
            "topic",
            "topic_name",
            "source_scope",
            "source_scope_name",
            "last_run",
            "title",
            "url",
            "domain",
            "snippet",
            "content",
            "favicon_url",
            "score",
            "published_at",
            "matched_queries",
            "first_seen_at",
            "last_seen_at",
            "is_new",
            "is_saved",
            "saved_title",
            "folder",
            "folder_name",
            "created_at",
            "updated_at",
        )
