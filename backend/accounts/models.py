from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user from day one so fields can be added later without a painful migration."""
