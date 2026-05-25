from collections import OrderedDict

from django.contrib.auth import authenticate
from django.http.response import HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import urlsafe_base64_decode

from appointment.models import Appointment
from doctor.forms import DoctorForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import message

from doctor.models import Doctor
from .forms import LoginForm, UserForm
from .models import User, UserProfile
from django.contrib import messages, auth
from .utils import detectUser, send_verification_email
from django.contrib.auth.decorators import login_required, user_passes_test

from django.core.exceptions import PermissionDenied


def check_role_vendor(user):
    if user.role == 1:
        return True
    else:
        raise PermissionDenied


def check_role_customer(user):
    if user.role == 2:
        return True
    else:
        raise PermissionDenied


def check_role_pharmacist(user):
    if user.role == 3:
        return True
    else:
        raise PermissionDenied


def registerUser(request):
    if request.user.is_authenticated:
        messages.warning(request, 'You are already logged in!')
        return redirect('dashboard')
    elif request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            phone_number = form.cleaned_data['phone_number']
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                password=password
            )
            user.phone_number = phone_number
            user.role = User.CUSTOMER
            user.save()

            mail_subject = 'Please activate your account'
            email_template = 'accounts/email/account_verification_email.html'
            send_verification_email(request, user, mail_subject, email_template)

            messages.success(request, 'Your account has been registered sucessfully!')
            return redirect('registerUser')
        else:
            print('invalid form')
            print(form.errors)
    else:
        form = UserForm()
    context = {
        'form': form,
    }
    return render(request, 'accounts/registerUser.html', context)


def registerDoctor(request):
    if request.user.is_authenticated:
        messages.warning(request, 'You are already logged in!')
        return redirect('dashboard')
    elif request.method == 'POST':
        form = UserForm(request.POST)
        v_form = DoctorForm(request.POST, request.FILES)
        if form.is_valid() and v_form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            phone_number = form.cleaned_data['phone_number']
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                password=password
            )
            user.phone_number = phone_number
            user.role = User.DOCTOR
            user.is_admin = True
            user.save()
            vendor = v_form.save(commit=False)
            vendor.user = user
            user_profile = UserProfile.objects.get(user=user)
            vendor.user_profile = user_profile
            vendor.save()

            mail_subject = 'Please activate your account'
            email_template = 'accounts/email/account_verification_email.html'
            print("sending activation mail")
            send_verification_email(request, user, mail_subject, email_template)

            messages.success(request, 'Activation mail has been sent. Please activate your account.')
            return redirect('login')
        else:
            print('invalid form')
            print(form.errors)
    else:
        form = UserForm()
        v_form = DoctorForm()

    context = {
        'form': form,
        'v_form': v_form,
    }

    return render(request, 'accounts/registerDoctor.html', context)


def registerPharmacist(request):
    if request.user.is_authenticated:
        messages.warning(request, 'You are already logged in!')
        return redirect('dashboard')
    elif request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            phone_number = form.cleaned_data['phone_number']
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                password=password
            )
            user.phone_number = phone_number
            user.role = User.PHARMACIST
            user.save()

            mail_subject = 'Please activate your account'
            email_template = 'accounts/email/account_verification_email.html'
            send_verification_email(request, user, mail_subject, email_template)

            messages.success(request, 'Activation mail has been sent. Please activate your account.')
            return redirect('login')
        else:
            print('invalid form')
            print(form.errors)
    else:
        form = UserForm()

    return render(request, 'accounts/registerPharmacist.html', {'form': form})


def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        if user.role == 2:
            messages.success(request, 'Congratulation! Your account is activated.')
        else:
            messages.success(request, 'Congratulation! Your account is activated. Please wait for the admin to approve your account.')
        return redirect('myAccount')
    else:
        messages.error(request, 'Invalid activation link')
        return redirect('myAccount')


from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
from django.shortcuts import render, redirect

def login(request):
    if request.user.is_authenticated:
        messages.warning(request, 'You are already logged in!')
        return redirect('myAccount')

    form = LoginForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.cleaned_data['user']
            auth_login(request, user)
            messages.success(request, 'You are now logged in.')

            if user.is_doctor():
                doctor = Doctor.objects.get(user=user)
                if not doctor.clinic_address or not doctor.contact_phone or not doctor.department:
                    return redirect('doctor')

            elif user.is_customer():
                user_profile = UserProfile.objects.get(user=user)
                if not user_profile.gender or not user_profile.address:
                    return redirect('customer')

            return redirect('myAccount')

        messages.error(request, 'Please correct the highlighted errors.')

    return render(request, 'accounts/login.html', {'form': form})


def logout(request):
    auth.logout(request)
    messages.info(request, 'You are logged out.')
    return redirect('login')


@login_required(login_url='login')
def myAccount(request):
    user = request.user
    redirectUrl = detectUser(user)
    return redirect(redirectUrl)


@login_required(login_url='login')
@user_passes_test(check_role_customer)
def custDashboard(request):
    profile = UserProfile.objects.get(user=request.user)
    customer = User.objects.get(pk=request.user.id)

    appointments_qs = Appointment.objects.select_related(
        'doctor',
        'doctor__user',
        'doctor__user__userprofile',
        'patient',
        'time_slot'
    ).filter(
        patient=customer
    ).order_by('-appointment_date', '-time_slot__start_time', '-id')

    grouped_appointments = OrderedDict()

    for appointment in appointments_qs:
        if hasattr(appointment, 'conversation'):
            appointment.has_conversation = True
            appointment.conversation_id = appointment.conversation.id
        else:
            appointment.has_conversation = False
            appointment.conversation_id = ''

        doctor_id = appointment.doctor.id

        if doctor_id not in grouped_appointments:
            grouped_appointments[doctor_id] = {
                'doctor': appointment.doctor,
                'appointments': []
            }

        grouped_appointments[doctor_id]['appointments'].append(appointment)

    context = {
        'profile': profile,
        'appointments': appointments_qs,
        'grouped_appointments': grouped_appointments.values(),
    }
    return render(request, 'accounts/custDashboard.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_pharmacist)
def pharmacistDashboard(request):
    return redirect('pharmacist_dashboard')


from django.utils.timezone import now

@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def doctorDashboard(request):
    doctor = Doctor.objects.get(user=request.user)

    appointments_qs = Appointment.objects.select_related(
        'patient',
        'patient__userprofile',
        'time_slot'
    ).filter(
        doctor=doctor
    ).order_by('-appointment_date', '-time_slot__start_time', '-id')

    grouped_appointments = OrderedDict()

    for appointment in appointments_qs:
        if hasattr(appointment, 'conversation'):
            appointment.has_conversation = True
            appointment.conversation_id = appointment.conversation.id
        else:
            appointment.has_conversation = False
            appointment.conversation_id = ''

        patient_id = appointment.patient.id

        if patient_id not in grouped_appointments:
            grouped_appointments[patient_id] = {
                'patient': appointment.patient,
                'appointments': []
            }

        grouped_appointments[patient_id]['appointments'].append(appointment)

    appointment_count = appointments_qs.count()

    patient_count = Appointment.objects.filter(
        doctor=doctor
    ).values('patient').distinct().count()

    today_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=now().date()
    ).count()

    context = {
        'appointments': appointments_qs,
        'grouped_appointments': grouped_appointments.values(),
        'now': now(),
        'appointment_count': appointment_count,
        'patient_count': patient_count,
        'today_appointments': today_appointments,
    }

    return render(request, 'accounts/doctorDashboard.html', context)


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email__exact=email)

            mail_subject = 'Reset Your Password'
            email_template = 'accounts/email/reset_password_email.html'
            send_verification_email(request, user, mail_subject, email_template)

            messages.success(request, 'Password reset link has been sent to your email address.')
            return redirect('login')
        else:
            messages.error(request, 'Account does not exist')
            return redirect('forgot_password')
    return render(request, 'accounts/forgot_password.html')


def reset_password_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.info(request, 'Please reset your password')
        return redirect('reset_password')

    else:
        messages.error(request, 'This link has been expired!')
        return redirect('myAccount')


def reset_password(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            print("password matched")
            print("uid", request.session.get('uid'))
            print("all sessions", request.session.items())
            pk = request.session.get('uid')
            user = User.objects.get(pk=pk)
            user.set_password(password)
            user.is_active = True
            user.save()
            messages.success(request, 'Password reset successful')
            return redirect('login')
        else:
            messages.error(request, 'Password do not match!')
            return redirect('reset_password')
    return render(request, 'accounts/reset_password.html')


def change_password(request):
    profile = UserProfile.objects.get(user=request.user)
    if request.method == 'POST':
        current_password = request.POST['current_password']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        email = request.user.email
        print("email", email)
        print("password", password)

        if password == confirm_password:
            user = auth.authenticate(email=email, password=current_password)
            if user is not None:
                user.set_password(password)
                user.is_active = True
                user.save()
                messages.success(request, 'Password changed successfully')
                redirect('login')
            else:
                messages.error(request, 'Current password is incorrect')
        else:
            messages.error(request, 'Passwords do not match!')
        return redirect('change_password')
    context = {
        "profile": profile
    }
    return render(request, 'accounts/change_password.html', context)


def change_password_view(request):
    return redirect('change_password')