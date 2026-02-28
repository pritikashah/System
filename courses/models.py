from django.db import models
from django.conf import settings
import uuid

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    course_code = models.CharField(max_length=20)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'teacher'}
    )

    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='enrolled_courses',
        blank=True,
        limit_choices_to={'user_type': 'student'}
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.course.title}"
    
class LiveClass(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="live_classes")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'teacher'}
    )
    title = models.CharField(max_length=200)
    scheduled_time = models.DateTimeField()
    room_name = models.CharField(max_length=200, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.room_name:
            self.room_name = f"class-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.course.title}"
