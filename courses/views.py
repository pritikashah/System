from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.timezone import localtime
from notifications.utils import create_notification
from .models import Course, Lesson, LiveClass, Material, Assignment, Submission
from datetime import timedelta
from notifications.models import Notification
from notifications.utils import send_deadline_notifications
from .models import Attendance
from django.urls import reverse
import secrets
import string


# -------------------- COURSE CODE GENERATION --------------------

def generate_course_code(length=8):
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def generate_unique_course_code(length=8):
    code = generate_course_code(length=length)
    while Course.objects.filter(course_code=code).exists():
        code = generate_course_code(length=length)
    return code


# -------------------- CREATE COURSE --------------------

@login_required
def create_course(request):
    if request.user.user_type != "teacher":
        messages.error(request, "Only teachers can create courses.")
        return redirect("student_dashboard")

    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        manual_code = request.POST.get('course_code')
        auto_generate = request.POST.get('auto_generate')

        if auto_generate:
            code = generate_unique_course_code()
        else:
            if not manual_code:
                messages.error(request, "Course code is required.")
                return redirect('create_course')
            code = manual_code
            if Course.objects.filter(course_code=code).exists():
                messages.error(request, "Course code already exists. Please choose another.")
                return redirect("create_course")

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
    if request.user.user_type != "student":
        messages.error(request, "Only students can enroll in courses.")
        return redirect("teacher_dashboard")

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
    live_classes = LiveClass.objects.filter(course=course).select_related("teacher").order_by("scheduled_time")
    materials = course.materials.all()
    assignments = course.assignments.all()
    now = timezone.now()

    if request.user.user_type == "student":
        for assignment in assignments:
            submission = Submission.objects.filter(
                assignment=assignment,
                student=request.user
            ).first()

            if submission:
                assignment.submitted = True
                assignment.is_late = localtime(submission.submitted_at) > localtime(assignment.due_date)
            else:
                assignment.submitted = False
                assignment.is_late = False

    for live_class in live_classes:
        live_class.can_join_now = now >= live_class.scheduled_time
    
    send_deadline_notifications()

    return render(request, 'course_detail.html', {
        'course': course,
        'lessons': lessons,
        'live_classes': live_classes,
        'materials': materials,
        'assignments': assignments,
        'now': localtime(now),
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
        if timezone.now() < live_class.scheduled_time:
            messages.error(request, "This class has not started yet.")
            return redirect("student_dashboard")
        attendance, created = Attendance.objects.get_or_create(
            live_class=live_class,
            student=request.user,
            defaults={
                "status": "present" if timezone.now() <= live_class.scheduled_time + timedelta(minutes=10) else "late"
            }
        )
        if not created:
            attendance.join_count += 1
            attendance.save()
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
            messages.success(request, "Live class scheduled successfully.")
            for student in course.students.all():
                link = reverse('course_detail', args=[course.id])
                create_notification(
                    student,
                    f"New live class scheduled for {course.title}: {title}",
                    link
                )
        else:
            messages.error(request, "Both title and scheduled time are required.")

        return redirect('course_detail', course_id=course.id)

    return render(request, "create_live_class.html", {"course": course})


@login_required
def meeting(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.user.user_type == "teacher":
        if request.user != course.created_by:
            return redirect("teacher_dashboard")
    elif request.user.user_type == "student":
        if request.user not in course.students.all():
            return redirect("student_dashboard")
    else:
        return redirect("login")

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
        for student in course.students.all():
            link = reverse('course_detail', args=[course.id])
            create_notification(
                student,
                f"New material uploaded in {course.title}: {title}",
                link
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
        assignment = Assignment.objects.create(
            course=course,
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            due_date=request.POST.get("due_date"),
            created_by=request.user
        )

        students = course.students.all()
        for student in students:
            link = reverse('course_detail', args=[course.id])
            create_notification(
                student,
                f"New assignment posted in {course.title}: {assignment.title}",
                link
            )
        return redirect("course_detail", course_id=course.id)

    return render(request, "create_assignment.html", {"course": course})


@login_required
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)

    if request.user.user_type != "student":
        messages.error(request, "Only students can submit assignments.")
        return redirect("teacher_dashboard")

    if request.user not in assignment.course.students.all():
        messages.error(request, "You must be enrolled in this course to submit.")
        return redirect("course_list")

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
        link = reverse('view_submissions', args=[assignment.id])
        create_notification(
            assignment.course.created_by,
            f"{request.user.username} submitted {assignment.title}",
            link
        )
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

@login_required
def course_attendance(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    live_classes = course.live_classes.all()
    total_classes = live_classes.count()

    attendance_records = Attendance.objects.filter(
        student=request.user,
        live_class__course=course
    )

    attended_classes = attendance_records.count()

    percentage = 0
    if total_classes > 0:
        percentage = (attended_classes / total_classes) * 100

    return render(request, "course_attendance.html", {
        "course": course,
        "total_classes": total_classes,
        "attended_classes": attended_classes,
        "percentage": round(percentage, 2),
        "records": attendance_records,
        "live_classes": live_classes
    })

@login_required
def overall_attendance(request):
    courses = request.user.enrolled_courses.all()

    total_classes = 0
    attended_classes = 0

    course_data = []

    for course in courses:
        live_classes = course.live_classes.count()
        attended = Attendance.objects.filter(
            student=request.user,
            live_class__course=course
        ).count()

        total_classes += live_classes
        attended_classes += attended

        percentage = (attended / live_classes * 100) if live_classes > 0 else 0

        course_data.append({
            "course": course,
            "percentage": round(percentage, 2)
        })

    overall_percentage = (attended_classes / total_classes * 100) if total_classes > 0 else 0

    return render(request, "overall_attendance.html", {
        "total_classes": total_classes,
        "attended_classes": attended_classes,
        "overall_percentage": round(overall_percentage, 2),
        "course_data": course_data
    })

from django.db.models import Count
from .models import Attendance, LiveClass

@login_required
def teacher_attendance_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Only teacher allowed
    if request.user != course.created_by:
        return redirect("teacher_dashboard")

    live_classes = LiveClass.objects.filter(course=course).order_by("-scheduled_time")

    data = []

    for live_class in live_classes:
        records = Attendance.objects.filter(live_class=live_class).select_related("student")

        # students who attended
        attended_students = [r.student for r in records]

        # all students in course
        all_students = course.students.all()

        # absent students
        absent_students = [s for s in all_students if s not in attended_students]

        data.append({
            "live_class": live_class,
            "records": records,
            "absent_students": absent_students
        })

    return render(request, "teacher_attendance.html", {
        "course": course,
        "data": data
    })