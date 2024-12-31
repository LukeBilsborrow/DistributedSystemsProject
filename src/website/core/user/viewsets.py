from django.shortcuts import get_object_or_404
from core.user.serializers import UserSerializer
from core.user.models import User
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import filters


class UserViewSet(viewsets.ModelViewSet):
    http_method_names = ["get"]
    serializer_class = UserSerializer
    permission_classes = IsAuthenticated
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["updated"]
    ordering = ["-updated"]

    def get_queryset(self):
        if not self.request.user.is_superuser:
            raise TypeError("You are not authorized to view this page.")

        return User.objects.all()

    def get_object(self):
        queryset = self.get_queryset()
        lookup_field_value = self.kwargs[self.lookup_field]

        # obj = queryset.get(username=lookup_field_value)
        lookup_field = self.lookup_field
        obj = get_object_or_404(queryset, **{lookup_field: lookup_field_value})
        self.check_object_permissions(self.request, obj)

        return obj
