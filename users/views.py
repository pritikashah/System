from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .models import CustomUser
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from django.utils.timezone import localtime

from courses.models import Course, LiveClass


def _apply_word_search(queryset, query, fields):
    if not query:
        return queryset

    words = [word.strip() for word in query.split() if word.strip()]
    if not words:
        return queryset

    for word in words:
        per_word_filter = Q()
        for field in fields:
            per_word_filter |= Q(**{f"{field}__icontains": word})
        queryset = queryset.filter(per_word_filter)
    return queryset


def _build_suggestions(courses, live_classes):
    suggestion_pool = []
    for course in courses:
        suggestion_pool.extend((course.title or "").split())
        suggestion_pool.extend((course.description or "").split())
        suggestion_pool.append(course.course_code or "")

    for live_class in live_classes:
        suggestion_pool.extend((live_class.title or "").split())

    suggestions = []
    seen = set()
    for token in suggestion_pool:
        cleaned = token.strip(".,!?()[]{}\"'").lower()
        if len(cleaned) < 2 or cleaned in seen:
            continue
        seen.add(cleaned)
        suggestions.append(cleaned)
    return sorted(suggestions)[:200]

@login_required
def student_dashboard(request):
    query = request.GET.get("q", "").strip()
    courses = request.user.enrolled_courses.all().order_by("title")
    courses = _apply_word_search(
        courses,
        query,
        ["title", "description", "course_code", "created_by__username"],
    )

    live_classes = list(
        LiveClass.objects.filter(course__in=courses)
        .select_related("course", "teacher")
        .order_by("scheduled_time")
    )
    now = timezone.now()
    for live_class in live_classes:
        live_class.can_join_now = now >= live_class.scheduled_time
        live_class.local_scheduled_time = localtime(live_class.scheduled_time)

    suggestions = _build_suggestions(courses, live_classes)

    return render(
        request,
        'student_dashboard.html',
        {
            'courses': courses,
            'live_classes': live_classes,
            'search_query': query,
            'search_suggestions': suggestions,
            'now': localtime(now),
        },
    )

@login_required
def teacher_dashboard(request):
    query = request.GET.get("q", "").strip()
    courses = Course.objects.filter(created_by=request.user).order_by("title")
    courses = _apply_word_search(
        courses,
        query,
        ["title", "description", "course_code"],
    )

    live_classes = list(
        LiveClass.objects.filter(course__in=courses)
        .select_related("course")
        .order_by("scheduled_time")
    )
    suggestions = _build_suggestions(courses, live_classes)

    return render(
        request,
        'teacher_dashboard.html',
        {
            'courses': courses,
            'live_classes': live_classes,
            'search_query': query,
            'search_suggestions': suggestions,
            'now': localtime(timezone.now()),
        },
    )

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_type = request.POST.get('user_type')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type=user_type
        )

        login(request, user)

        if user.user_type == 'teacher':
            return redirect('teacher_dashboard')
        else:
            return redirect('student_dashboard')

    return render(request, 'register.html')

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.user_type == 'teacher':
                return redirect('teacher_dashboard')
            else:
                return redirect('student_dashboard')
        else:
            messages.error(request, "Invalid credentials")

    return render(request, 'login.html')


def user_logout(request):
    logout(request)
    return redirect('login')
