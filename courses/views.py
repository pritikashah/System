from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Course
from django.http import HttpResponseForbidden

@login_required
def create_course(request):
    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')

        Course.objects.create(
            title=title,
            description=description,
            created_by=request.user
        )

        return redirect('teacher_dashboard')

    return render(request, 'create_course.html')

@login_required
def course_list(request):
    courses = Course.objects.all()
    return render(request, 'course_list.html', {'courses': courses})

@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.user.user_type == 'student':
        if not course.students.filter(id=request.user.id).exists():
            course.students.add(request.user)

    return redirect('student_dashboard')

@login_required
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.user != course.created_by:
        return redirect('teacher_dashboard')

    course.delete()
    return redirect('teacher_dashboard')
