from core.user.models import User
from rest_framework import serializers
from core.transcription.models import TranscriptionSubmission


class TranscriptionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = TranscriptionSubmission
        username = serializers.CharField(source="user.username", read_only=True)

        fields = ["transcription_id", "username", "status", "name", "visibility"]
        read_only_field = [
            "transcription_id",
            "username",
            "status",
            "name",
            "visibility",
        ]
