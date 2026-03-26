from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from notifications.utils import create_notification
from .models import Course, Lesson, LiveClass, Material, Assignment, Submission

import secrets
import string


# -------------------- COURSE CODE GENERATION --------------------

def generate_course_code(length=8):
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


# -------------------- CREATE COURSE --------------------

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


# -------------------- COURSE LIST --------------------

@login_required
def course_list(request):
    courses = Course.objects.all()
    return render(request, 'course_list.html', {'courses': courses})


# -------------------- ENROLL COURSE --------------------

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

        create_notification(
            course.created_by,
            f"{request.user.username} enrolled in your course {course.title}"
        )

        messages.success(request, "Enrollment successful!")
        return redirect('student_dashboard')

    return redirect('course_list')


# -------------------- DELETE COURSE --------------------

@login_required
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.user != course.created_by:
        return redirect('teacher_dashboard')

    course.delete()
    return redirect('teacher_dashboard')


# -------------------- COURSE DETAIL --------------------

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Student access
    if request.user.user_type == 'student':
        if request.user not in course.students.all():
            return redirect('student_dashboard')

    # Teacher access
    if request.user.user_type == 'teacher':
        if request.user != course.created_by:
            return redirect('teacher_dashboard')

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
    materials = course.materials.all()
    assignments = course.assignments.all()

    # ✅ Submission status
    assignment_status = {}

    if request.user.user_type == "student":
        for assignment in assignments:
            submitted = Submission.objects.filter(
                assignment=assignment,
                student=request.user
            ).exists()

            assignment_status[assignment.id] = submitted

    return render(request, 'course_detail.html', {
        'course': course,
        'lessons': lessons,
        'live_classes': live_classes,
        'materials': materials,
        'assignments': assignments,
        'assignment_status': assignment_status
    })


# -------------------- LIVE CLASS --------------------

@login_required
def join_live_class(request, class_id):
    live_class = get_object_or_404(LiveClass, id=class_id)

    if request.user.user_type == "teacher":
        if live_class.teacher != request.user:
            return redirect("teacher_dashboard")

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


# -------------------- MATERIAL --------------------

@login_required
def upload_material(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.user != course.created_by:
        return redirect('teacher_dashboard')

    if request.method == "POST":
        title = request.POST.get("title")
        file = request.FILES.get("file")

        if not file:
            messages.error(request, "Please select a file.")
            return redirect("course_detail", course_id=course.id)

        allowed_extensions = ['pdf', 'doc', 'docx', 'ppt', 'pptx']
        file_extension = file.name.split('.')[-1].lower()

        if file_extension not in allowed_extensions:
            messages.error(request, "Only PDF, DOC, and PPT files are allowed.")
            return redirect("course_detail", course_id=course.id)

        Material.objects.create(
            course=course,
            title=title,
            file=file,
            uploaded_by=request.user
        )

        return redirect("course_detail", course_id=course.id)

    return render(request, "upload_material.html", {"course": course})


@login_required
def delete_material(request, material_id):
    material = get_object_or_404(Material, id=material_id)

    if request.user != material.course.created_by:
        return redirect("course_detail", course_id=material.course.id)

    material.delete()
    return redirect("course_detail", course_id=material.course.id)


# -------------------- ASSIGNMENT --------------------

@login_required
def create_assignment(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.user != course.created_by:
        return redirect("teacher_dashboard")

    if request.method == "POST":
        Assignment.objects.create(
            course=course,
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            due_date=request.POST.get("due_date"),
            created_by=request.user
        )

        return redirect("course_detail", course_id=course.id)

    return render(request, "create_assignment.html", {"course": course})


@login_required
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)

    # ✅ Prevent duplicate submission
    if Submission.objects.filter(assignment=assignment, student=request.user).exists():
        messages.error(request, "You have already submitted this assignment.")
        return redirect("course_detail", course_id=assignment.course.id)

    if request.method == "POST":
        file = request.FILES.get("file")

        Submission.objects.create(
            assignment=assignment,
            student=request.user,
            file=file
        )

        messages.success(request, "Assignment submitted successfully!")
        return redirect("course_detail", course_id=assignment.course.id)

    return render(request, "submit_assignment.html", {"assignment": assignment})


@login_required
def view_submissions(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)

    if request.user != assignment.course.created_by:
        return redirect("teacher_dashboard")

    submissions = assignment.submissions.all()

    return render(request, "view_submissions.html", {
        "assignment": assignment,
        "submissions": submissions
    })