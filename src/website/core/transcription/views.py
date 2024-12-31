from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render

from core.transcription.models import TranscriptionSubmission
from rest_framework.views import APIView

from core.transcription.serializers import TranscriptionSerializer
from rest_framework.response import Response
from django.template import loader
from io import BytesIO
from django.shortcuts import redirect
from django.template import loader
import pysubs2
import os

RESULT_OUTPUT_ROOT = os.environ.get("RESULT_OUTPUT_ROOT")


class TranscriptionResult(APIView):
    def get(self, request, **kwargs):
        try:
            transcription_id = kwargs.get("id")
            print(request.GET)
            format_type = request.GET.get("format_type")
            print(f"format_type: {format_type}")
            transcription = get_object_or_404(
                TranscriptionSubmission, transcription_id=transcription_id
            )

            if (
                transcription.visibility == "private"
                and request.user != transcription.user
            ):
                return Response(status=403)

            target_file = os.path.join(RESULT_OUTPUT_ROOT, f"{transcription_id}.srt")

            if format_type == "vtt":
                subs = pysubs2.load(target_file, encoding="utf-8")

                target_file = os.path.join(
                    RESULT_OUTPUT_ROOT, f"{transcription_id}.{format_type}"
                )
                subs.save(target_file, encoding="utf-8")

            else:
                format_type = "srt"

            with open(target_file, "rb") as f:
                content = f.read()

            file_stream = BytesIO(content)

            response = FileResponse(file_stream)
            response["Content-Disposition"] = (
                f'attachment; filename="transcription.{format_type}"'
            )
            return response
        except Exception as e:
            print(e)
            return Response(status=500)


class TranscriptionDetail(APIView):
    def get(self, request, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/login/")

        transcription_id = kwargs.get("id")

        transcription = get_object_or_404(
            TranscriptionSubmission, transcription_id=transcription_id
        )

        if (
            transcription.visibility == "private"
            and not transcription.user == request.user
        ):
            return Response(status=403)

        serializer = TranscriptionSerializer(transcription)
        template = loader.get_template("transcription_detail.html")
        context = {
            "transcription_data": serializer.data,
        }
        return HttpResponse(template.render(context, request))


def transcription_list(request):
    transcriptions = TranscriptionSubmission.objects.all()
    transcriptions = transcriptions.filter(status="completed", visibility="public")
    template = loader.get_template("transcription_list.html")
    context = {
        "transcriptions": transcriptions,
    }

    return HttpResponse(template.render(context, request))
