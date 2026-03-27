from django.shortcuts import render
from .models import Notification
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


@login_required
def notification_list(request):

    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by("-created_at")

    return render(request, "notifications_dropdown.html", {
        "notifications": notifications
    })

def unread_notification_count(request):
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return JsonResponse({"unread_count": count})

@login_required
def mark_notifications_read(request):

    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    return JsonResponse({"status": "success"})
