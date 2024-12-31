"""
URL configuration for webRoot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from core.submit.views import (
    processing_request_result_submit,
)
from core.auth.views import login_view, register_view

from core.user.views import UserPage
from core.views import index_view

from django.contrib import admin
from django.urls import path, re_path

from core.transcription.views import (
    TranscriptionDetail,
    TranscriptionResult,
    transcription_list,
)
from core.submit.views import submit_request_request_handler

from django.contrib.auth import views as auth_views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", index_view, name="home"),
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("submit/", submit_request_request_handler, name="submit"),
    path("result_submit/", processing_request_result_submit, name="result-submit"),
    path("transcriptions/", transcription_list, name="transcriptions"),
    # alter this endpoint to allow a query string
    re_path(
        r"transcription_result/(?P<id>\d+)/$",
        TranscriptionResult.as_view(),
        name="transcription_result",
    ),
    path("profile/", UserPage.as_view(), name="profile"),
    path(
        "transcription_detail/<int:id>/",
        TranscriptionDetail.as_view(),
        name="transcription-detail",
    ),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
