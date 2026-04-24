from django.shortcuts import render

def login_view(request):
    return render(request, 'gateway/login.html')

def register_view(request):
    return render(request, 'gateway/register.html')

def dashboard_view(request):
    return render(request, 'gateway/dashboard.html')

def fields_view(request):
    return render(request, 'gateway/fields.html')

def diagnosis_view(request):
    return render(request, 'gateway/diagnosis.html')

def notifications_view(request):
    return render(request, 'gateway/notifications.html')

def weather_view(request):
    return render(request, 'gateway/weather.html')

def admin_view(request):
    return render(request, 'gateway/admin_panel.html')

def history_view(request):
    return render(request, 'gateway/history.html')