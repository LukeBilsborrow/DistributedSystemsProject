from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)


class UserManager(BaseUserManager):

    def create_user(self, username, password=None, **kwargs):
        """Create and return a `User` with an email, phone number, username and password."""
        if username is None:
            raise TypeError("Users must have a username.")
        if password is None:
            raise TypeError("Users must have a password.")

        user = self.model(username=username)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, username, password):
        """
        Create and return a `User` with superuser (admin) permissions.
        """
        if username is None:
            raise TypeError("Users must have a username.")
        if password is None:
            raise TypeError("Users must have a password.")

        user = self.create_user(username, password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(db_index=True, max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    quota = models.IntegerField(default=20, validators=[MinValueValidator(0)])
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["password"]

    objects = UserManager()

    def __str__(self):
        return f"{self.username}"


def validate_user_data(data_dict):
    if "username" not in data_dict:
        return False
    if "password" not in data_dict:
        return False
    return True
