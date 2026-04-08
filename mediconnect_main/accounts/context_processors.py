from datetime import datetime

from accounts.models import User, UserProfile
from doctor.models import Doctor
from django.conf import settings


def get_doctor(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except:
        doctor = None

    return dict(doctor=doctor)


def get_user_profile(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except:
        user_profile = None

    user_age = None
    if user_profile and user_profile.date_of_birth:
        user_age = (datetime.now().date() - user_profile.date_of_birth).days // 365

    return {
        'user_profile': user_profile,
        'user_age': user_age,
    }


def get_google_api(request):
    return {'GOOGLE_API_KEY': settings.GOOGLE_API_KEY}


def get_doctors(request):
    doctors = Doctor.objects.select_related('user__userprofile').all()
    for doctor in doctors:
        doctor.user_profile = doctor.user.userprofile
    return dict(doctors=doctors)


def get_users(request):
    users = User.objects.select_related('userprofile').all()
    for user in users:
        print(user.userprofile.phone_number)
    return dict(users=users)