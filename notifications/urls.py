from django.urls import path
from . import views

urlpatterns = [
    path("", views.notification_list, name="notifications"),
    path("unread-count/", views.unread_notification_count, name="unread_count"),
    path("mark-read/", views.mark_notifications_read, name="mark_notifications_read"),
]
    