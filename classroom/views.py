from django.shortcuts import render

def student_dashboard(request):
    return render(request, 'classroom/student_dashboard.html')

def teacher_dashboard(request):
    return render(request, 'classroom/teacher_dashboard.html')
