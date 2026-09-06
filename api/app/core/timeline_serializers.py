from rest_framework import serializers

from .models import TopicTimelineSummary


class TopicTimelineSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicTimelineSummary
        fields = ("id", "generated_at", "model_name", "entries", "created_at", "updated_at")
