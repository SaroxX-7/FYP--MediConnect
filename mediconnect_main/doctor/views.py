from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail, BadHeaderError
from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from accounts.forms import UserProfileForm, UserInfoForm
from accounts.utils import send_notification
from .forms import DoctorForm, EducationForm, ExperienceForm, AwardForm, MembershipForm, RegistrationForm
from .models import Doctor, Education, Experience, Award, Membership, Registration
from appointment.models import Appointment, Booking
from django.forms import inlineformset_factory
from accounts.models import UserProfile, Department
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Prefetch
from appointment.models import Appointment, Remark, RemarkMedicine
from pharmacy.models import Medicine
from doctor.models import Doctor

def doctor_appointment_details(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related(
            'doctor',
            'doctor__user',
            'patient',
            'time_slot'
        ).prefetch_related(
            Prefetch(
                'remarks',
                queryset=Remark.objects.select_related(
                    'doctor',
                    'doctor__user'
                ).prefetch_related(
                    Prefetch(
                        'medicines',
                        queryset=RemarkMedicine.objects.select_related('medicine')
                    )
                ).order_by('-created_at')
            )
        ),
        pk=appointment_id
    )

    medicines = Medicine.objects.all()
    doctor = get_object_or_404(Doctor, user=request.user)

    # get existing remark for this appointment by this doctor
    existing_remark = appointment.remarks.filter(doctor=doctor).first()

    if request.method == 'POST':
        if existing_remark:
            # update existing remark
            remark = existing_remark
            remark.diagnosis = request.POST.get('diagnosis')
            remark.symptoms = request.POST.get('symptoms')
            remark.note = request.POST.get('note')
            remark.advice = request.POST.get('advice')
            remark.follow_up_date = request.POST.get('follow_up_date') or None
            remark.save()
        else:
            # create new remark only once
            remark = Remark.objects.create(
                appointment=appointment,
                doctor=doctor,
                diagnosis=request.POST.get('diagnosis'),
                symptoms=request.POST.get('symptoms'),
                note=request.POST.get('note'),
                advice=request.POST.get('advice'),
                follow_up_date=request.POST.get('follow_up_date') or None,
            )

        medicine_ids = request.POST.getlist('medicine_id[]')
        dosages = request.POST.getlist('dosage[]')
        quantities = request.POST.getlist('quantity[]')
        frequencies = request.POST.getlist('frequency[]')
        durations = request.POST.getlist('duration[]')
        instructions = request.POST.getlist('instruction[]')

        # remove old medicines before adding updated ones
        remark.medicines.all().delete()

        for i in range(len(medicine_ids)):
            if medicine_ids[i]:
                medicine = get_object_or_404(Medicine, id=medicine_ids[i])

                RemarkMedicine.objects.create(
                    remark=remark,
                    medicine=medicine,
                    dosage=dosages[i] if i < len(dosages) else '',
                    quantity=quantities[i] if i < len(quantities) and quantities[i] else 1,
                    frequency=frequencies[i] if i < len(frequencies) else '',
                    duration=durations[i] if i < len(durations) else '',
                    instruction=instructions[i] if i < len(instructions) else '',
                )

        appointment = get_object_or_404(
            Appointment.objects.select_related(
                'doctor',
                'doctor__user',
                'patient',
                'time_slot'
            ).prefetch_related(
                Prefetch(
                    'remarks',
                    queryset=Remark.objects.select_related(
                        'doctor',
                        'doctor__user'
                    ).prefetch_related(
                        Prefetch(
                            'medicines',
                            queryset=RemarkMedicine.objects.select_related('medicine')
                        )
                    ).order_by('-created_at')
                )
            ),
            pk=appointment_id
        )

    remarks = appointment.remarks.all()
    latest_remark = appointment.remarks.filter(doctor=doctor).first()
    remark_medicines = latest_remark.medicines.all() if latest_remark else []

    return render(request, 'doctors/appointment_details.html', {
        'appointment': appointment,
        'medicines': medicines,
        'remarks': remarks,
        'latest_remark': latest_remark,
        'remark_medicines': remark_medicines,
    })
# EducationFormSet = inlineformset_factory(Doctor, Education, form=EducationForm, extra=1)
# ExperienceFormSet = inlineformset_factory(Doctor, Experience, form=ExperienceForm, extra=1)
# AwardsFormSet = inlineformset_factory(Doctor, Award, form=AwardForm, extra=1)
# MembershipFormSet = inlineformset_factory(Doctor, Membership, form=MembershipForm, extra=1)
# RegistrationFormSet = inlineformset_factory(Doctor, Registration, form=RegistrationForm, extra=1)
EducationFormSet = inlineformset_factory(Doctor, Education, form=EducationForm, extra=1, can_delete=True)
ExperienceFormSet = inlineformset_factory(Doctor, Experience, form=ExperienceForm, extra=1, can_delete=True)
AwardsFormSet = inlineformset_factory(Doctor, Award, form=AwardForm, extra=1, can_delete=True)
MembershipFormSet = inlineformset_factory(Doctor, Membership, form=MembershipForm, extra=1, can_delete=True)
RegistrationFormSet = inlineformset_factory(Doctor, Registration, form=RegistrationForm, extra=1, can_delete=True)

# @login_required(login_url='login')
# def dprofile(request):
#     profile = get_object_or_404(UserProfile, user=request.user)
#     doctor = get_object_or_404(Doctor, user=request.user)
#     print(doctor, profile)
#     if request.method == 'POST':
#         profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
#         user_form = UserInfoForm(request.POST, instance=request.user)
#         doctor_form = DoctorForm(request.POST, request.FILES, instance=doctor)
#         if doctor_form.is_valid() and profile_form.is_valid() and user_form.is_valid():
#             profile_form.save()
#             user_form.save()
#             created_doctor = doctor_form.save()
#             education_formset = EducationFormSet(request.POST, instance=created_doctor)
#             experience_formset = ExperienceFormSet(request.POST, instance=created_doctor)
#             award_formset = AwardsFormSet(request.POST, instance=created_doctor)
#             membership_formset = MembershipFormSet(request.POST, instance=created_doctor)
#             registration_formset = RegistrationFormSet(request.POST, instance=created_doctor)
#
#             if education_formset.is_valid() and experience_formset.is_valid():
#                 education_formset.save()
#                 experience_formset.save()
#                 award_formset.save()
#                 membership_formset.save()
#                 registration_formset.save()
#                 messages.success(request, "Profile updated successfully")
#
#             else:
#                 print(education_formset.errors)
#                 print(experience_formset.errors)
#                 print(award_formset.errors)
#                 print(membership_formset.errors)
#                 print(registration_formset.errors)
#
#     else:
#         user_form = UserInfoForm(instance=request.user)
#         profile_form = UserProfileForm(instance=profile)
#         doctor_form = DoctorForm(instance=doctor)
#         education_formset = EducationFormSet(instance=doctor)
#         experience_formset = ExperienceFormSet(instance=doctor)
#         award_formset = AwardsFormSet(instance=doctor)
#         membership_formset = MembershipFormSet(instance=doctor)
#         registration_formset = RegistrationFormSet(instance=doctor)
#
#     context = {
#         'user_form': user_form,
#         'doctor': doctor,
#         'profile_form': profile_form,
#         'doctor_form': doctor_form,
#         'education_formset': education_formset,
#         'experience_formset': experience_formset,
#         'award_formset': award_formset,
#         'membership_formset': membership_formset,
#         'registration_formset': registration_formset,
#     }
#     return render(request, 'doctors/dprofile.html', context )


@login_required(login_url='login')
def dprofile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    doctor = get_object_or_404(Doctor, user=request.user)
    departments = Department.objects.all()
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        user_form = UserInfoForm(request.POST, instance=request.user)
        doctor_form = DoctorForm(request.POST, request.FILES, instance=doctor)

        # Validate and save main forms first
        main_forms_valid = doctor_form.is_valid() and profile_form.is_valid() and user_form.is_valid()
        if main_forms_valid:
            doctor_form.save()
            profile_form.save()
            user_form.save()
            messages.success(request, "Profile information updated successfully.")

        # Handle formsets separately
        formsets = [
            EducationFormSet(request.POST, instance=doctor),
            ExperienceFormSet(request.POST, instance=doctor),
            AwardsFormSet(request.POST, instance=doctor),
            MembershipFormSet(request.POST, instance=doctor),
            RegistrationFormSet(request.POST, instance=doctor),
        ]
        formsets_valid = all(fs.is_valid() for fs in formsets)
        if formsets_valid:
            for fs in formsets:
                fs.save()
            if main_forms_valid:
                messages.success(request, "Full profile updated successfully.")
        elif not formsets_valid and main_forms_valid:
            messages.info(request,
                          "Main profile information saved, but some additional details were not updated due to errors or being left blank.")

        if not main_forms_valid:
            messages.error(request, "There was an error with the main profile information.")
    else:
        # Initialize forms and formsets for GET request
        profile_form = UserProfileForm(instance=profile)
        user_form = UserInfoForm(instance=request.user)
        doctor_form = DoctorForm(instance=doctor)
        formsets = [
            EducationFormSet(instance=doctor),
            ExperienceFormSet(instance=doctor),
            AwardsFormSet(instance=doctor),
            MembershipFormSet(instance=doctor),
            RegistrationFormSet(instance=doctor),
        ]

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'doctor_form': doctor_form,
        'formsets': formsets,
        'departments': departments,
    }
    return render(request, 'doctors/dprofile.html', context)


def doctor_detail(request, doctor_slug):

    doctor = get_object_or_404(Doctor.objects.select_related('user__userprofile'), doctor_slug=doctor_slug)
    print(doctor.user.userprofile.profile_picture.url)

    context = {
        'doctor': doctor,
    }
    return render(request, 'doctors/doctorPage.html', context)

# views.py
from appointment.models import TimeSlot
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

@require_http_methods(["POST"])
def add_time_slot(request):
    try:
        if request.body:
            doctor = Doctor.objects.get(user=request.user)
            data = json.loads(request.body)
            TimeSlot.objects.create(
                doctor=doctor,
                day=data['day'],
                start_time=data['start_time'],
                end_time=data['end_time'],
                availability=data.get('availability', True)
            )
            messages.success(request, 'Time slot added successfully!')
            return redirect('time_slots')  # Adjust to your correct view
        else:
            messages.error(request, 'Empty request body')
            return redirect(request.META.get('HTTP_REFERER', 'fallback_view'))  # Redirect back or to a fallback view
    except json.JSONDecodeError:
        messages.error(request, 'Invalid JSON')
    except Doctor.DoesNotExist:
        messages.error(request, 'Doctor not found')
    except KeyError as e:
        messages.error(request, f'Missing field in data: {e}')
    except Exception as e:
        messages.error(request, str(e))

    return redirect(request.META.get('HTTP_REFERER', 'fallback_view'))

def edit_time_slot(request, slot_id):
    time_slot = get_object_or_404(TimeSlot, pk=slot_id)
    if request.method == 'POST':
        # Update the time slot with new data
        time_slot.day = request.POST['day']
        time_slot.start_time = request.POST['start_time']
        time_slot.end_time = request.POST['end_time']
        time_slot.save()
        return redirect('time_slots')

# def delete_time_slot(request, slot_id):
#     if request.method == 'POST':
#         time_slot = get_object_or_404(TimeSlot, pk=slot_id)
#         time_slot.delete()
#         return JsonResponse({'message': 'Time slot deleted successfully'})
@require_http_methods(["POST"])
def delete_time_slot(request, slot_id):
    try:
        # Retrieve the time slot by ID
        time_slot = TimeSlot.objects.get(pk=slot_id, doctor__user=request.user)
        # Only allow deletion if the doctor owns the time slot
        if time_slot.doctor.user != request.user:
            return JsonResponse({'error': 'Unauthorized access'}, status=403)

        # Delete the time slot
        time_slot.delete()
        return JsonResponse({'message': 'Time slot deleted successfully'}, status=200)

    except TimeSlot.DoesNotExist:
        # Time slot not found
        return JsonResponse({'error': 'Time slot not found'}, status=404)
    except Exception as e:
        # General error handling
        return JsonResponse({'error': str(e)}, status=500)

def time_slots(request):
    doctor = Doctor.objects.get(user=request.user)
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    current_day = days[datetime.now().weekday()]
    slots_by_day = {day: TimeSlot.objects.filter(doctor=doctor, day=day) for day in days}
    return render(request, 'doctors/time_slots.html', {'slots_by_day': slots_by_day, 'doctor': doctor, 'current_day': current_day, 'days': days})


from django.utils.timezone import now
def appointments(request):
    doctor = Doctor.objects.get(user=request.user)
    appointments = Appointment.objects.filter(doctor=doctor).order_by('-appointment_date')
    context = {
        'appointments': appointments,
        'now': now(),
    }
    return render(request, 'doctors/appointments.html', context)

from datetime import datetime
def dashboard_view(request):
    print('Doctor Dashboard')
    # Fetch all appointments or filter based on some criteria
    appointments = Appointment.objects.all().order_by('-appointment_date')
    now = datetime.now()
    return render(request, 'accounts/doctorDashboard.html', {'appointments': appointments, 'now': now,})

def accept_appointment(request, appointment_id):
    appointment = Appointment.objects.get(id=appointment_id)
    appointment.appointment_status = 'confirmed'
    appointment.save()

    patient_email = appointment.patient.email
    patient_name = appointment.patient.first_name + ' ' + appointment.patient.last_name
    patient_username = appointment.patient.username
    doctor_name = appointment.doctor.user.first_name + ' ' + appointment.doctor.user.last_name

    appointment_id = appointment.id
    appointment_date = appointment.appointment_date
    appointment_time = appointment.time_slot.start_time
    appointment_status = appointment.appointment_status

    subject = "Appointment Acceptance Email"

    context = {
        "to_email": patient_email,
        "name": patient_name,
        "username": patient_username,
        "doctor_name": doctor_name,
        "appointment_id": appointment_id,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "appointment_status": appointment_status,
    }

    mail_template = 'accounts/email/appointment_accept_mail.html'
    try:
        send_notification(subject, mail_template, context)
    except BadHeaderError:
        return HttpResponse('Invalid header found')
    messages.success(request, 'Appointment Accepted')

    return redirect('doctor')


# def reject_appointment(request, appointment_id):
#     appointment = Appointment.objects.get(id=appointment_id)
#     appointment.appointment_status = 'cancelled'
#     appointment.time_slot.availability = True
#     appointment.save()
#
#     appointment_date = appointment.appointment_date
#     appointment_time = appointment.time_slot.start_time
#     appointment_status = appointment.appointment_status
#
#     patient_email = appointment.patient.email
#     patient_name = appointment.patient.first_name + ' ' + appointment.patient.last_name
#     doctor_name = appointment.doctor.user.first_name + ' ' + appointment.doctor.user.last_name
#
#     subject = "Appointment Rejection Email"
#
#     context = {
#                 "to_email": patient_email,
#         "name": patient_name,
#         "doctor_name": doctor_name,
#         "appointment_id": appointment_id,
#         "appointment_date": appointment_date,
#         "appointment_time": appointment_time,
#         "appointment_status": appointment_status,
#     }
#
#     mail_template = 'accounts/email/appointment_reject_mail.html'
#
#     try:
#         send_notification(subject, mail_template, context)
#
#     except BadHeaderError:
#         return HttpResponse('Invalid header found')
#
#     messages.error(request, 'Appointment Rejected')
#
#     return redirect('doctor')

def reject_appointment(request, appointment_id):
    with transaction.atomic():
        appointment = get_object_or_404(Appointment, id=appointment_id)

        # Retrieve and delete or update the associated booking
        try:
            booking = Booking.objects.get(time_slot=appointment.time_slot, date=appointment.appointment_date)
            booking.delete()  # or update the status if you want to keep a record
        except Booking.DoesNotExist:
            messages.error(request, "No booking record found for this appointment.")
            return redirect('doctor')  # Adjust as needed

        # Update appointment status and release the time slot
        appointment.appointment_status = 'cancelled'
        appointment.time_slot.availability = True
        appointment.save()

    # Prepare email notification details
    patient_email = appointment.patient.email
    patient_name = appointment.patient.first_name + ' ' + appointment.patient.last_name
    doctor_name = appointment.doctor.user.first_name + ' ' + appointment.doctor.user.last_name
    subject = "Appointment Rejection Email"
    context = {
        "to_email": patient_email,
        "name": patient_name,
        "doctor_name": doctor_name,
        "appointment_id": appointment_id,
        "appointment_date": appointment.appointment_date,
        "appointment_time": appointment.time_slot.start_time,
        "appointment_status": appointment.appointment_status,
    }
    mail_template = 'accounts/email/appointment_reject_mail.html'

    # Send email notification
    try:
        send_notification(subject, mail_template, context)
    except BadHeaderError:
        return HttpResponse('Invalid header found')

    messages.error(request, 'Appointment Rejected')
    return redirect('doctor')  # Adjust the redirect as needed based on your URL configuration


def appointment_details(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    return render(request, 'doctors/appointment_details.html', {'appointment': appointment})
