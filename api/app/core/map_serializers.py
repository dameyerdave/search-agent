from rest_framework import serializers


class SearchResultMapPreviewSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    url = serializers.URLField()
    topic_name = serializers.CharField()
    source_scope_name = serializers.CharField(allow_null=True, required=False)
    domain = serializers.CharField(allow_blank=True)
    published_at = serializers.DateTimeField(allow_null=True)
    is_new = serializers.BooleanField()


class SearchResultMapMarkerSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    display_name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    place_type = serializers.CharField(allow_blank=True)
    related_result_count = serializers.IntegerField()
    remaining_result_count = serializers.IntegerField()
    results = SearchResultMapPreviewSerializer(many=True)


class SearchResultMapResponseSerializer(serializers.Serializer):
    result_count = serializers.IntegerField()
    mapped_result_count = serializers.IntegerField()
    location_count = serializers.IntegerField()
    markers = SearchResultMapMarkerSerializer(many=True)
