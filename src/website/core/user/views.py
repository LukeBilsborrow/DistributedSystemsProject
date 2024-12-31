from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.template import loader
from core.transcription.models import TranscriptionSubmission
from django.shortcuts import redirect


class UserPage(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")
        user = request.user
        transcriptions = TranscriptionSubmission.objects.filter(user=user)
        template = loader.get_template("user_page.html")

        context = {
            "username": user.username,
            "transcription_requests": transcriptions,
        }
        return HttpResponse(template.render(context, request))
