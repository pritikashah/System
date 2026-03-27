from .models import Notification
from django.utils import timezone
from datetime import timedelta
from courses.models import Assignment

def create_notification(user, message, link=None):
    Notification.objects.create(
        user=user,
        message=message,
        link=link
    )

def send_deadline_notifications():
    now = timezone.now()
    one_hour_later = now + timedelta(hours=1)

    assignments = Assignment.objects.filter(
        due_date__lte=one_hour_later,
        due_date__gt=now,
        deadline_notified=False
    )

    for assignment in assignments:
        students = assignment.course.students.all()

        for student in students:
            create_notification(
                student,
                f"⏰ Assignment '{assignment.title}' deadline is in 1 hour!"
            )

        assignment.deadline_notified = True
        assignment.save()