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

    return dict(user_profile=user_profile)


def get_google_api(request):
    return {'GOOGLE_API_KEY': settings.GOOGLE_API_KEY}

# def get_stripe_public_key(request):
#     return {'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY}

# def get_doctors(request):
#     doctors = Doctor.objects.all()
#     return dict(doctors=doctors)

def get_doctors(request):
    # Using select_related to fetch related UserProfile in the same query
    doctors = Doctor.objects.select_related('user__userprofile').all()
    for doctor in doctors:
        doctor.user_profile = doctor.user.userprofile
    return dict(doctors=doctors)


def get_users(request):
    # Assume you have User model imported and it's the one connected to UserProfile
    users = User.objects.select_related('userprofile').all()  # Efficiently prefetch UserProfile objects
    for user in users:
        # Now you can access UserProfile directly via user.userprofile
        print(user.userprofile.phone_number)  # Example usage
    return dict(users=users)
