from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Course, Lesson, LiveClass
import secrets
import string


def generate_course_code(length=8):
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


@login_required
def create_course(request):
    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        manual_code = request.POST.get('course_code')
        auto_generate = request.POST.get('auto_generate')

        if auto_generate:
            code = generate_course_code()
        else:
            if not manual_code:
                messages.error(request, "Course code is required.")
                return redirect('create_course')
            code = manual_code

        Course.objects.create(
            title=title,
            description=description,
            course_code=code,
            created_by=request.user
        )

        messages.success(request, f"Course created successfully! Code: {code}")
        return redirect('teacher_dashboard')

    return render(request, 'create_course.html')


@login_required
def course_list(request):
    courses = Course.objects.all()
    return render(request, 'course_list.html', {'courses': courses})


@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        if request.user in course.students.all():
            messages.error(request, "You are already enrolled.")
            return redirect('course_list')

        entered_code = request.POST.get('course_code')

        if not entered_code:
            messages.error(request, "Course code is required.")
            return redirect('course_list')

        if entered_code != course.course_code:
            messages.error(request, "Invalid course code.")
            return redirect('course_list')

        course.students.add(request.user)
        messages.success(request, "Enrollment successful!")
        return redirect('student_dashboard')

    return redirect('course_list')


@login_required
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.user != course.created_by:
        return redirect('teacher_dashboard')

    course.delete()
    return redirect('teacher_dashboard')


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Student access control
    if request.user.user_type == 'student':
        if request.user not in course.students.all():
            return redirect('student_dashboard')

    # Teacher access control
    if request.user.user_type == 'teacher':
        if request.user != course.created_by:
            return redirect('teacher_dashboard')

        # Teacher can add lessons
        if request.method == "POST":
            title = request.POST.get('title')
            content = request.POST.get('content')

            if title and content:
                Lesson.objects.create(
                    course=course,
                    title=title,
                    content=content
                )

    lessons = course.lessons.all()
    live_classes = LiveClass.objects.filter(course=course)

    return render(request, 'course_detail.html', {
        'course': course,
        'lessons': lessons,
        'live_classes': live_classes
    })


@login_required
def join_live_class(request, class_id):
    live_class = get_object_or_404(LiveClass, id=class_id)

    # Teacher access
    if request.user.user_type == "teacher":
        if live_class.teacher != request.user:
            return redirect("teacher_dashboard")

    # Student access
    elif request.user.user_type == "student":
        if request.user not in live_class.course.students.all():
            return redirect("student_dashboard")

    return render(request, "join_class.html", {
        "live_class": live_class,
        "room_name": live_class.room_name
    })


@login_required
def create_live_class(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Only course creator can create live class
    if request.user != course.created_by:
        return redirect('teacher_dashboard')

    if request.method == "POST":
        title = request.POST.get("title")
        scheduled_time = request.POST.get("scheduled_time")

        if title and scheduled_time:
            LiveClass.objects.create(
                course=course,
                teacher=request.user,
                title=title,
                scheduled_time=scheduled_time
            )

        return redirect('course_detail', course_id=course.id)

    return render(request, "create_live_class.html", {"course": course})
def meeting(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    room_name = f"course_{course.id}"
    return render(request, "meeting.html", {"room_name": room_name})
