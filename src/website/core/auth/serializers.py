from django.forms import ValidationError
from django.http import JsonResponse
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.password_validation import validate_password
from core.user.serializers import UserSerializer
from core.user.models import User


class LoginSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        data["user"] = UserSerializer(self.user).data
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return data


class RegistrationSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["username", "password"]

    def validate(self, attrs):
        data = super().validate(attrs)
        validate_password(data["password"])
        return data

    def create(self, validated_data):
        try:
            user = User.objects.get(username=validated_data["username"])
        except ObjectDoesNotExist:
            user = User.objects.create_user(**validated_data)
        return user
