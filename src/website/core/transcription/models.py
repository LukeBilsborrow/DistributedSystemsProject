from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TranscriptionSubmission(models.Model):
    transcription_id = models.AutoField(primary_key=True, unique=True)
    status = models.CharField(max_length=200, null=False)
    date_submitted = models.DateTimeField("date submitted", auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200, null=True)
    visibility = models.CharField(max_length=20, null=True)

    def __str__(self):
        return f"Transcription ID: {self.transcription_id}"