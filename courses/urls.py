from django.urls import path
from django.shortcuts import redirect

from . import views

urlpatterns = [
    path('create-course/', views.create_course, name='create_course'),
    path('courses/', views.course_list, name='course_list'),
    path('enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('delete-course/<int:course_id>/', views.delete_course, name='delete_course'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
     path("live-class/<int:class_id>/", views.join_live_class, name="join_live_class"),
     path('', lambda request: redirect('login')),

]
