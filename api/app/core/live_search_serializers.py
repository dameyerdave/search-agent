from rest_framework import serializers

from .models import SourceScope
from .serializers import clean_string_list


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
