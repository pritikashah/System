from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .models import CustomUser
from django.contrib.auth.decorators import login_required
from courses.models import Course

@login_required
def student_dashboard(request):
    courses = request.user.enrolled_courses.all()
    return render(request, 'student_dashboard.html', {'courses': courses})

@login_required
def teacher_dashboard(request):
    courses = Course.objects.filter(created_by=request.user)
    return render(request, 'teacher_dashboard.html', {'courses': courses})

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
