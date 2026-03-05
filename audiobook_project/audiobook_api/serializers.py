from rest_framework import serializers

class AudiobookRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=200)
    duration = serializers.IntegerField(default=10, min_value=1, max_value=60)
    emotion = serializers.ChoiceField(
        choices=['cheerful', 'serious', 'mystery', 'neutral'],
        default='neutral'
    )

class SegmentSerializer(serializers.Serializer):
    text = serializers.CharField()
    start_time = serializers.FloatField()
    end_time = serializers.FloatField()
    duration = serializers.FloatField()

class AudiobookResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    audio_url = serializers.URLField(required=False)
    firebase_id = serializers.CharField(required=False)
    topic = serializers.CharField(required=False)
    duration = serializers.IntegerField(required=False)
    emotion = serializers.CharField(required=False)
    segments = SegmentSerializer(many=True, required=False)
    segment_count = serializers.IntegerField(required=False)
    word_count = serializers.IntegerField(required=False)
    generation_time = serializers.CharField(required=False)
    error = serializers.CharField(required=False)