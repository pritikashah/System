from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.conf import settings

class CustomUser(AbstractUser):

    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    )

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return self.username
