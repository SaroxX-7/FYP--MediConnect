from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.mail import BadHeaderError
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods
from django.db.models import Prefetch
from django.forms import inlineformset_factory
from django.utils.timezone import now
from django.template.loader import get_template
from datetime import datetime
import json

from appointment.models import Appointment, Booking, TimeSlot, Remark, RemarkMedicine
from doctor.models import Doctor, DoctorBilling
from accounts.forms import UserProfileForm, UserInfoForm
from accounts.utils import send_notification
from .forms import (
    DoctorForm, EducationForm, ExperienceForm, AwardForm,
    MembershipForm, RegistrationForm, DoctorBillingForm
)
from .models import Education, Experience, Award, Membership, Registration
from accounts.models import UserProfile, Department
from pharmacy.models import Medicine

# Try to import xhtml2pdf, handle if not installed
try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False
    pisa = None


@login_required
def appointment_details(request, appointment_id):
    return doctor_appointment_details(request, appointment_id)


@login_required
def doctor_appointment_details(request, appointment_id):
    doctor = get_object_or_404(Doctor, user=request.user)

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
        pk=appointment_id,
        doctor=doctor
    )

    medicines = Medicine.objects.all()

    doctor_time_slots = TimeSlot.objects.filter(
        doctor=doctor,
        availability=True
    ).order_by('day', 'start_time')

    previous_appointments = Appointment.objects.filter(
        patient=appointment.patient,
        doctor=doctor,
        appointment_date__lt=appointment.appointment_date
    ).order_by('-appointment_date')[:5]

    existing_remark = appointment.remarks.filter(doctor=doctor).first()

    if request.method == 'POST':
        follow_up_date_str = request.POST.get('follow_up_date')
        follow_up_date = parse_date(follow_up_date_str) if follow_up_date_str else None

        if follow_up_date and follow_up_date < timezone.localdate():
            messages.error(request, "Follow-up date cannot be in the past.")
            return redirect('doctor_appointment_details', appointment_id=appointment.id)

        if existing_remark:
            remark = existing_remark
            remark.diagnosis = request.POST.get('diagnosis')
            remark.symptoms = request.POST.get('symptoms')
            remark.note = request.POST.get('note')
            remark.advice = request.POST.get('advice')
            remark.follow_up_date = follow_up_date
            remark.save()
        else:
            remark = Remark.objects.create(
                appointment=appointment,
                doctor=doctor,
                diagnosis=request.POST.get('diagnosis'),
                symptoms=request.POST.get('symptoms'),
                note=request.POST.get('note'),
                advice=request.POST.get('advice'),
                follow_up_date=follow_up_date,
            )

        medicine_ids = request.POST.getlist('medicine_id[]')
        dosages = request.POST.getlist('dosage[]')
        quantities = request.POST.getlist('quantity[]')
        frequencies = request.POST.getlist('frequency[]')
        durations = request.POST.getlist('duration[]')
        instructions = request.POST.getlist('instruction[]')

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

        messages.success(request, 'Remark updated successfully.')
        return redirect('doctor_appointment_details', appointment_id=appointment.id)

    remarks = appointment.remarks.all()
    latest_remark = appointment.remarks.filter(doctor=doctor).first()
    remark_medicines = latest_remark.medicines.all() if latest_remark else []

    remark_follow_up_date = None
    if latest_remark and latest_remark.follow_up_date:
        remark_follow_up_date = latest_remark.follow_up_date

    return render(request, 'doctors/appointment_details.html', {
        'appointment': appointment,
        'doctor': doctor,
        'doctor_time_slots': doctor_time_slots,
        'medicines': medicines,
        'remarks': remarks,
        'latest_remark': latest_remark,
        'remark_medicines': remark_medicines,
        'remark_follow_up_date': remark_follow_up_date,
        'previous_appointments': previous_appointments,
        'now': now(),
    })


EducationFormSet = inlineformset_factory(Doctor, Education, form=EducationForm, extra=1, can_delete=True)
ExperienceFormSet = inlineformset_factory(Doctor, Experience, form=ExperienceForm, extra=1, can_delete=True)
AwardsFormSet = inlineformset_factory(Doctor, Award, form=AwardForm, extra=1, can_delete=True)
MembershipFormSet = inlineformset_factory(Doctor, Membership, form=MembershipForm, extra=1, can_delete=True)
RegistrationFormSet = inlineformset_factory(Doctor, Registration, form=RegistrationForm, extra=1, can_delete=True)


@login_required(login_url='login')
def dprofile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    doctor = get_object_or_404(Doctor, user=request.user)
    billing, created = DoctorBilling.objects.get_or_create(doctor=doctor)

    departments = Department.objects.all()

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        user_form = UserInfoForm(request.POST, instance=request.user)
        doctor_form = DoctorForm(request.POST, request.FILES, instance=doctor)
        billing_form = DoctorBillingForm(request.POST, instance=billing)

        main_forms_valid = (
            doctor_form.is_valid()
            and profile_form.is_valid()
            and user_form.is_valid()
            and billing_form.is_valid()
        )

        if main_forms_valid:
            doctor_form.save()
            profile_form.save()
            user_form.save()
            billing_form.save()
            messages.success(request, "Profile and billing information updated successfully.")

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
            messages.info(
                request,
                "Main profile and billing information were saved, but some additional details were not updated due to errors or blank values."
            )

        if not main_forms_valid:
            messages.error(request, "There was an error in the profile or billing information.")

    else:
        profile_form = UserProfileForm(instance=profile)
        user_form = UserInfoForm(instance=request.user)
        doctor_form = DoctorForm(instance=doctor)
        billing_form = DoctorBillingForm(instance=billing)

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
        'billing_form': billing_form,
        'formsets': formsets,
        'departments': departments,
    }
    return render(request, 'doctors/dprofile.html', context)


def doctor_detail(request, doctor_slug):
    doctor = get_object_or_404(
        Doctor.objects.select_related('user__userprofile'),
        doctor_slug=doctor_slug
    )

    context = {
        'doctor': doctor,
    }
    return render(request, 'doctors/doctorPage.html', context)


@require_http_methods(["POST"])
@login_required
def add_time_slot(request):
    try:
        doctor = Doctor.objects.get(user=request.user)

        if request.body:
            data = json.loads(request.body)

            TimeSlot.objects.create(
                doctor=doctor,
                day=data['day'],
                start_time=data['start_time'],
                end_time=data['end_time'],
                availability=data.get('availability', True)
            )

            return JsonResponse({
                'success': True,
                'message': 'Time slot added successfully!'
            })

        return JsonResponse({
            'success': False,
            'message': 'Empty request body'
        }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON'
        }, status=400)

    except Doctor.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Doctor not found'
        }, status=404)

    except KeyError as e:
        return JsonResponse({
            'success': False,
            'message': f'Missing field in data: {e}'
        }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
def edit_time_slot(request, slot_id):
    time_slot = get_object_or_404(TimeSlot, pk=slot_id, doctor__user=request.user)

    if request.method == 'POST':
        time_slot.day = request.POST['day']
        time_slot.start_time = request.POST['start_time']
        time_slot.end_time = request.POST['end_time']
        time_slot.save()
        return redirect('time_slots')

    return redirect('time_slots')


@require_http_methods(["POST"])
@login_required
def delete_time_slot(request, slot_id):
    try:
        time_slot = TimeSlot.objects.get(pk=slot_id, doctor__user=request.user)
        time_slot.delete()

        return JsonResponse({
            'success': True,
            'message': 'Time slot deleted successfully'
        }, status=200)

    except TimeSlot.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Time slot not found'
        }, status=404)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
def time_slots(request):
    doctor = get_object_or_404(Doctor, user=request.user)
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    current_day = datetime.now().strftime('%A')

    slots_by_day = {
        day: TimeSlot.objects.filter(doctor=doctor, day=day).order_by('start_time')
        for day in days
    }

    return render(request, 'doctors/time_slots.html', {
        'slots_by_day': slots_by_day,
        'doctor': doctor,
        'current_day': current_day,
        'days': days
    })


@login_required
def appointments(request):
    doctor = get_object_or_404(Doctor, user=request.user)
    appointments = Appointment.objects.filter(doctor=doctor).order_by('-appointment_date', '-id')

    context = {
        'appointments': appointments,
        'now': now(),
    }
    return render(request, 'doctors/appointments.html', context)


@login_required
def dashboard_view(request):
    doctor = get_object_or_404(Doctor, user=request.user)

    appointments = Appointment.objects.select_related(
        'patient',
        'patient__userprofile',
        'time_slot'
    ).prefetch_related(
        Prefetch(
            'remarks',
            queryset=Remark.objects.select_related('doctor').prefetch_related(
                Prefetch(
                    'medicines',
                    queryset=RemarkMedicine.objects.select_related('medicine')
                )
            ).order_by('-created_at')
        )
    ).filter(
        doctor=doctor
    ).order_by('-appointment_date', '-id')

    appointment_count = appointments.count()
    patient_count = Appointment.objects.filter(
        doctor=doctor
    ).values('patient').distinct().count()

    today_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=now().date()
    ).count()

    context = {
        'appointments': appointments,
        'now': now(),
        'appointment_count': appointment_count,
        'patient_count': patient_count,
        'today_appointments': today_appointments,
    }

    return render(request, 'accounts/doctorDashboard.html', context)


@login_required
def accept_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related('doctor__user', 'patient', 'time_slot'),
        id=appointment_id,
        doctor__user=request.user
    )

    if appointment.appointment_status != 'pending':
        messages.error(request, 'Only pending appointments can be accepted.')
        return redirect('doctor')

    try:
        appointment.appointment_status = 'confirmed'
        appointment.save()

        patient_email = appointment.patient.email
        patient_name = appointment.patient.first_name + ' ' + appointment.patient.last_name
        patient_username = appointment.patient.username
        doctor_name = appointment.doctor.user.first_name + ' ' + appointment.doctor.user.last_name

        subject = "Appointment Acceptance Email"

        context = {
            "to_email": patient_email,
            "name": patient_name,
            "username": patient_username,
            "doctor_name": doctor_name,
            "appointment_id": appointment.id,
            "appointment_date": appointment.appointment_date,
            "appointment_time": appointment.time_slot.start_time if appointment.time_slot else None,
            "appointment_status": appointment.appointment_status,
        }

        mail_template = 'accounts/email/appointment_accept_mail.html'

        try:
            send_notification(subject, mail_template, context)
        except BadHeaderError:
            messages.warning(request, 'Appointment accepted but email notification failed.')

        messages.success(request, f'Appointment #{appointment.id} has been accepted successfully.')

    except ValidationError as e:
        messages.error(request, f'Cannot accept appointment: {str(e)}')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')

    return redirect('doctor')


@login_required
def reject_appointment(request, appointment_id):
    with transaction.atomic():
        appointment = get_object_or_404(
            Appointment.objects.select_related('doctor__user', 'patient', 'time_slot'),
            id=appointment_id,
            doctor__user=request.user
        )

        if appointment.appointment_status not in ['pending', 'confirmed']:
            messages.error(request, 'Only pending or confirmed appointments can be cancelled.')
            return redirect('doctor')

        try:
            Booking.objects.filter(
                time_slot=appointment.time_slot,
                date=appointment.appointment_date
            ).delete()

            appointment.appointment_status = 'cancelled'
            appointment.save()

            if appointment.time_slot:
                appointment.time_slot.availability = True
                appointment.time_slot.save()

            patient_email = appointment.patient.email
            patient_name = appointment.patient.first_name + ' ' + appointment.patient.last_name
            doctor_name = appointment.doctor.user.first_name + ' ' + appointment.doctor.user.last_name
            subject = "Appointment Rejection Email"

            context = {
                "to_email": patient_email,
                "name": patient_name,
                "doctor_name": doctor_name,
                "appointment_id": appointment.id,
                "appointment_date": appointment.appointment_date,
                "appointment_time": appointment.time_slot.start_time if appointment.time_slot else None,
                "appointment_status": appointment.appointment_status,
            }

            mail_template = 'accounts/email/appointment_reject_mail.html'

            try:
                send_notification(subject, mail_template, context)
            except BadHeaderError:
                messages.warning(request, 'Appointment rejected but email notification failed.')

            messages.error(request, f'Appointment #{appointment.id} has been rejected.')

        except ValidationError as e:
            messages.error(request, f'Cannot reject appointment: {str(e)}')
        except Exception as e:
            messages.error(request, f'An unexpected error occurred: {str(e)}')

    return redirect('doctor')


@login_required
def complete_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related('doctor__user', 'patient', 'time_slot'),
        id=appointment_id,
        doctor__user=request.user
    )

    if appointment.appointment_status != 'confirmed':
        messages.error(request, 'Only confirmed appointments can be marked as completed.')
        return redirect('doctor_appointment_details', appointment_id=appointment.id)

    appointment.appointment_status = 'completed'
    appointment.save()

    messages.success(request, f'Appointment #{appointment.id} marked as completed successfully.')
    return redirect('doctor_appointment_details', appointment_id=appointment.id)


@login_required
@require_http_methods(["POST"])
def create_followup_appointment(request, appointment_id):
    doctor = get_object_or_404(Doctor, user=request.user)
    previous_appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)

    if previous_appointment.appointment_status != 'completed':
        messages.error(
            request,
            'Follow-up can only be created after the previous appointment is completed.'
        )
        return redirect('doctor_appointment_details', appointment_id=previous_appointment.id)

    appointment_date = parse_date(request.POST.get('appointment_date'))
    time_slot_id = request.POST.get('time_slot_id')
    message = request.POST.get('message', '')

    if not appointment_date or not time_slot_id:
        messages.error(request, 'Please select follow-up date and time slot.')
        return redirect('doctor_appointment_details', appointment_id=previous_appointment.id)

    if appointment_date < timezone.localdate():
        messages.error(request, 'Follow-up date cannot be in the past.')
        return redirect('doctor_appointment_details', appointment_id=previous_appointment.id)

    time_slot = get_object_or_404(
        TimeSlot,
        id=time_slot_id,
        doctor=doctor,
        availability=True
    )

    active_followup_exists = Appointment.objects.filter(
        patient=previous_appointment.patient,
        doctor=doctor,
        appointment_status__in=['pending', 'confirmed']
    ).exists()

    if active_followup_exists:
        messages.error(request, 'This patient already has an active appointment with you.')
        return redirect('doctor_appointment_details', appointment_id=previous_appointment.id)

    if Booking.objects.filter(time_slot=time_slot, date=appointment_date).exists():
        messages.error(request, 'Selected follow-up slot is already booked.')
        return redirect('doctor_appointment_details', appointment_id=previous_appointment.id)

    try:
        with transaction.atomic():
            Booking.objects.create(
                time_slot=time_slot,
                date=appointment_date,
                user=previous_appointment.patient
            )

            followup_appointment = Appointment.objects.create(
                time_slot=time_slot,
                doctor=doctor,
                patient=previous_appointment.patient,
                appointment_date=appointment_date,
                appointment_type='followup',
                appointment_status='pending',
                message=message
            )

        messages.success(request, 'Follow-up appointment created successfully.')
        return redirect('doctor_appointment_details', appointment_id=followup_appointment.id)

    except ValidationError as e:
        messages.error(request, f'Cannot create follow-up: {str(e)}')
        return redirect('doctor_appointment_details', appointment_id=previous_appointment.id)
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('doctor_appointment_details', appointment_id=previous_appointment.id)


@login_required
def get_available_time_slots(request):
    date = request.GET.get('date')
    if not date:
        return JsonResponse({'slots': []})

    try:
        doctor = get_object_or_404(Doctor, user=request.user)
        appointment_date = datetime.strptime(date, '%Y-%m-%d').date()
        day_name = appointment_date.strftime('%A')

        slots_qs = TimeSlot.objects.filter(
            doctor=doctor,
            day=day_name,
            availability=True
        ).order_by('start_time')

        booked_slot_ids = Booking.objects.filter(
            date=appointment_date,
            time_slot__doctor=doctor
        ).values_list('time_slot_id', flat=True)

        slots = []
        for slot in slots_qs.exclude(id__in=booked_slot_ids):
            slots.append({
                'id': slot.id,
                'start_time': slot.start_time.strftime('%I:%M %p'),
                'end_time': slot.end_time.strftime('%I:%M %p')
            })

        return JsonResponse({'slots': slots})

    except Exception as e:
        return JsonResponse({'slots': [], 'error': str(e)}, status=500)


@login_required
def prescription_view(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related('doctor__user', 'patient', 'time_slot'),
        id=appointment_id
    )

    latest_remark = appointment.remarks.order_by('-created_at').first()

    remark_medicines = []
    if latest_remark:
        remark_medicines = latest_remark.medicines.select_related('medicine').all()

    context = {
        'appointment': appointment,
        'latest_remark': latest_remark,
        'remark_medicines': remark_medicines,
    }
    return render(request, 'doctors/prescription.html', context)


@login_required
def download_prescription_pdf(request, appointment_id):
    if not XHTML2PDF_AVAILABLE:
        return HttpResponse(
            'PDF generation is not available. Please install xhtml2pdf using: pip install xhtml2pdf',
            status=500
        )

    appointment = get_object_or_404(
        Appointment.objects.select_related('doctor__user', 'patient', 'time_slot'),
        id=appointment_id
    )

    if request.user.is_authenticated:
        is_doctor = hasattr(request.user, 'doctor')
        is_patient = appointment.patient == request.user

        if not (is_doctor or is_patient):
            messages.error(request, 'You do not have permission to download this prescription.')
            return redirect('home')
    else:
        messages.error(request, 'Please login to download prescription.')
        return redirect('login')

    latest_remark = appointment.remarks.order_by('-created_at').first()

    remark_medicines = []
    if latest_remark:
        remark_medicines = latest_remark.medicines.select_related('medicine').all()

    template = get_template('doctors/prescription_pdf.html')
    html = template.render({
        'appointment': appointment,
        'latest_remark': latest_remark,
        'remark_medicines': remark_medicines,
        'generated_date': now(),
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{appointment.id}_{now().date()}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response, encoding='utf-8')

    if pisa_status.err:
        return HttpResponse(f'Error generating PDF: {pisa_status.err}', status=500)

    return response