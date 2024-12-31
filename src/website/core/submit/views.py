# views.py
from django.http import JsonResponse

import requests
import os

from .utils import (
    get_bytes_count_to_mb,
    get_seg_credit_val,
    get_seg_from_file_data,
    export_seg_to_bytes,
)
from core.transcription.models import TranscriptionSubmission
from django.template import loader
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from core.transcription.serializers import TranscriptionSerializer
from django.contrib.auth.decorators import login_required


SECRET_KEY = os.environ.get("SECRET_KEY")
REQUESTS_QUEUE_SUBMISSION_SERVER_URL = os.environ.get(
    "REQUESTS_QUEUE_SUBMISSION_SERVER_URL"
)

REQUESTS_QUEUE_SUBMISSION_SERVER_EXTERNAL_PORT = os.environ.get(
    "REQUESTS_QUEUE_SUBMISSION_SERVER_EXTERNAL_PORT"
)
REQUESTS_QUEUE_SUBMISSION_SERVER_SUBMISSION_ENDPOINT = os.environ.get(
    "REQUESTS_QUEUE_SUBMISSION_SERVER_SUBMISSION_ENDPOINT"
)

QUEUE_SUBMIT_URL = f"{REQUESTS_QUEUE_SUBMISSION_SERVER_URL}:{REQUESTS_QUEUE_SUBMISSION_SERVER_EXTERNAL_PORT}/{REQUESTS_QUEUE_SUBMISSION_SERVER_SUBMISSION_ENDPOINT}"
RESULT_OUTPUT_ROOT = os.environ.get("RESULT_OUTPUT_ROOT")

MAX_FILE_SIZE_MB = 10


def get_secret_key():
    return SECRET_KEY


def send_request_to_queue(data):
    # create multipart form data
    audio_segment = data["audio_segment"]
    audio_bytes = export_seg_to_bytes(audio_segment)

    json_data = {
        "transcription_id": data["transcription_id"],
    }

    response = requests.post(
        f"http://{QUEUE_SUBMIT_URL}",
        headers={"X-Secret-Key": SECRET_KEY},
        files={"file_data": audio_bytes},
        data=json_data,
        timeout=10,
    )

    response.raise_for_status()


@login_required(login_url="/login/")
def submit_request_request_handler(request):
    if request.method == "POST":
        transcription = handle_submit_post(request)
        serializer = TranscriptionSerializer(transcription)
        return JsonResponse(serializer.data)

    return handle_submit_get(request)


def handle_submit_get(request):
    template = loader.get_template("request_submit.html")

    context = {}
    return HttpResponse(template.render(context, request))


def handle_submit_post(request):
    """Handle user request submission"""

    if not request.user.is_authenticated:
        raise ValueError("User not authenticated")

    try:
        data = get_processing_request_values(request)
    except ValueError as _:
        raise ValueError("Missing required fields")

    # check file size is appropriate
    filesize_mb = get_bytes_count_to_mb(data["file_data"].size)

    if filesize_mb > MAX_FILE_SIZE_MB:
        raise ValueError("File size too large")

    # get audio from file data
    seg = get_seg_from_file_data(data["file_data"])
    del data["file_data"]
    data["audio_segment"] = seg

    # check user has enough credits
    submission_credit_value = get_seg_credit_val(seg)
    if request.user.quota < submission_credit_value:
        raise ValueError("Insufficient credits")
    request.user.quota -= submission_credit_value
    request.user.save()

    submission_model = TranscriptionSubmission(
        status="submitted",
        user=request.user,
        visibility=data["visibility"],
        name=data["name"],
    )

    submission_model.save()
    transcription_id = submission_model.transcription_id
    data["transcription_id"] = transcription_id

    send_request_to_queue(data)

    return submission_model


def get_processing_request_values(request):
    file_data = request.FILES.get("file_data")
    visibility = request.POST.get("visibility")
    name = request.POST.get("name")

    if not file_data or not visibility or not name:
        raise ValueError("Missing required fields")

    return {
        "file_data": file_data,
        "visibility": visibility,
        "name": name,
    }


@csrf_exempt
def processing_request_result_submit(request):

    try:
        request_data = parse_request_result(request)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    os.makedirs(RESULT_OUTPUT_ROOT, exist_ok=True)
    output_path = os.path.join(
        RESULT_OUTPUT_ROOT, f"{request_data['transcription_id']}.srt"
    )
    with open(output_path, "wb") as destination:
        for chunk in request_data["file_data"].chunks():
            destination.write(chunk)

    try:
        # update transcription status in database

        submission = TranscriptionSubmission.objects.get(
            transcription_id=request_data["transcription_id"]
        )

        submission.status = request_data["status"]

        submission.save()
    except BaseException as e:
        print(e)

        return JsonResponse({"error": "Transcription submission not found"}, status=400)

    return JsonResponse({"message": "Request processed successfully"})


def parse_request_result(request):
    # check request has custom auth header with secret key
    request_secret_key = request.headers.get("x-secret-key")

    if request_secret_key != SECRET_KEY:
        raise ValueError("Forbidden")

    transcription_id = request.POST.get("transcription_id")

    status = request.POST.get("status")

    if not transcription_id or not status:
        raise ValueError("Missing required fields")

    if status == "success":
        file_data = request.FILES.get("file_data")
        status = "completed"

        return {
            "file_data": file_data,
            "transcription_id": transcription_id,
            "status": status,
        }

    return {"status": status, "transcription_id": transcription_id}
