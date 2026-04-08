from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView
from django.utils.decorators import method_decorator

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from accounts.forms import UserInfoForm, UserProfileForm
from accounts.models import User, UserProfile, Department, Disease
from appointment.models import TimeSlot, Appointment, Booking, Remark, RemarkMedicine
from doctor.models import Doctor, Payment
from pharmacy.models import Medicine


def customer_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if request.user.role != User.CUSTOMER:
            return redirect('doctor')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required(login_url='login')
@customer_required
def cprofile(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        user_form = UserInfoForm(request.POST, instance=request.user)

        if profile_form.is_valid() and user_form.is_valid():
            profile_form.save()
            user_form.save()
            messages.success(request, 'Profile updated')
            return redirect('cprofile')
        else:
            print(profile_form.errors)
            print(user_form.errors)
    else:
        profile_form = UserProfileForm(instance=profile)
        user_form = UserInfoForm(instance=request.user)

    formatted_date = profile_form.instance.date_of_birth
    dob = profile.date_of_birth
    age = None
    if dob:
        age = (datetime.now().date() - dob).days // 365

    context = {
        'profile_form': profile_form,
        'user_form': user_form,
        'profile': profile,
        'formatted_date': formatted_date,
        'age': age,
    }
    return render(request, 'customers/cprofile.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(customer_required, name='dispatch')
class DoctorsByDepartmentView(ListView):
    model = Doctor
    template_name = 'customers/doctors_by_department.html'

    def get_queryset(self):
        department_slug = self.kwargs.get('department_slug')
        diseases_prefetch = Prefetch('department__disease', queryset=Disease.objects.all())

        queryset = Doctor.objects.filter(
            department__slug=department_slug
        ).select_related(
            'user__userprofile',
            'department'
        ).prefetch_related(
            diseases_prefetch
        )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        department_slug = self.kwargs.get('department_slug')
        context['department'] = Department.objects.filter(slug=department_slug).first()
        return context


@login_required
@customer_required
def search_doctors(request):
    query = request.GET.get('query', '').strip()

    doctors = Doctor.objects.select_related(
        'user',
        'department'
    ).prefetch_related(
        'department__disease'
    )

    if query:
        disease = Disease.objects.filter(name__iexact=query).first()
        department = Department.objects.filter(name__iexact=query).first()

        if disease:
            doctors = doctors.filter(department__disease=disease)
        elif department:
            doctors = doctors.filter(department=department)
        else:
            doctors = doctors.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(department__name__icontains=query) |
                Q(department__disease__name__icontains=query)
            ).distinct()
    else:
        doctors = Doctor.objects.none()

    doctors_list = [{
        "doctor": doctor,
        "department": doctor.department.name if doctor.department else "No department",
    } for doctor in doctors]

    context = {
        'doctors': doctors,
        'query': query,
        'object_list': doctors_list,
    }

    return render(request, 'customers/search_doctors.html', context)


@require_http_methods(["POST"])
@login_required
@customer_required
def book_appointment(request):
    time_slot_id = request.POST.get('time_slot_id')
    doctor_id = request.POST.get('doctor_id')
    patient_id = request.user.id
    appointment_type = request.POST.get('appointment_type')
    appointment_date_str = request.POST.get('appointment_date')
    payment_method = request.POST.get('payment_method', 'cash')
    message = request.POST.get('message', '')
    image_upload = request.FILES.get('image_upload')

    appointment_date = parse_date(appointment_date_str)
    if appointment_date is None:
        messages.error(request, "Invalid date format.")
        return HttpResponse("Invalid date format.", status=400)

    if appointment_type != 'checkup':
        messages.error(request, "You cannot create a follow-up appointment yourself.")
        return redirect('available_appointment', doctor_id=doctor_id)

    with transaction.atomic():
        doctor = get_object_or_404(
            Doctor.objects.select_related('billing'),
            id=doctor_id
        )
        time_slot = get_object_or_404(
            TimeSlot,
            id=time_slot_id,
            doctor=doctor,
            availability=True
        )

        existing_active_appointment = Appointment.objects.filter(
            patient=request.user,
            doctor=doctor,
            appointment_status__in=['pending', 'confirmed']
        ).exists()

        if existing_active_appointment:
            latest_active = Appointment.objects.filter(
                patient=request.user,
                doctor=doctor,
                appointment_status__in=['pending', 'confirmed']
            ).order_by('-id').first()

            messages.error(
                request,
                "You already have a pending or confirmed appointment with this doctor."
            )
            return redirect('appointment_details', appointment_id=latest_active.id)

        cancelled_booking = Appointment.objects.filter(
            patient=request.user,
            doctor=doctor,
            appointment_date=appointment_date,
            time_slot=time_slot,
            appointment_status='cancelled'
        ).first()

        if cancelled_booking:
            messages.warning(
                request,
                "Your previous booking for this slot has been cancelled."
            )
            return redirect('available_appointment', doctor_id=doctor_id)

        if Booking.objects.filter(time_slot=time_slot, date=appointment_date).exists():
            messages.error(request, "This time slot is already booked.")
            return HttpResponse("This slot is already booked.", status=400)

        billing = getattr(doctor, 'billing', None)

        consultation_fee = Decimal('0.00')
        esewa_number = ''
        esewa_enabled = False
        mediconnect_percentage = Decimal('10.00')

        if billing:
            consultation_fee = Decimal(str(billing.consultation_fee or 0)).quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            )
            esewa_number = billing.esewa_number or ''
            esewa_enabled = billing.esewa_enabled

        allowed_payment_methods = ['cash']
        if esewa_enabled and esewa_number:
            allowed_payment_methods.append('esewa')

        if payment_method not in allowed_payment_methods:
            messages.error(request, "Selected payment method is not available.")
            return HttpResponse("Invalid payment method.", status=400)

        mediconnect_fee = (
            (consultation_fee * mediconnect_percentage) / Decimal('100')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        total_amount = (
            consultation_fee + mediconnect_fee
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        Booking.objects.create(
            time_slot=time_slot,
            date=appointment_date,
            user=request.user
        )

        appointment = Appointment.objects.create(
            time_slot=time_slot,
            doctor=doctor,
            appointment_date=appointment_date,
            patient_id=patient_id,
            appointment_type='checkup',
            appointment_status='pending',
            message=message,
            image_upload=image_upload
        )

        payment = Payment.objects.create(
            appointment=appointment,
            doctor=doctor,
            patient=request.user,
            payment_method=payment_method,
            payment_status='pending',
            doctor_fee=consultation_fee,
            mediconnect_percentage=mediconnect_percentage,
            mediconnect_fee=mediconnect_fee,
            total_amount=total_amount
        )

    if payment_method == 'esewa':
        messages.success(request, "Your appointment has been booked. Please complete payment.")
        return redirect('esewa_pay', payment_id=payment.id)

    messages.success(request, "Your appointment has been successfully booked!")
    return redirect('appointment_details', appointment_id=appointment.id)


def get_week_dates(start_date=None):
    if start_date is None:
        start_date = datetime.today()
    start_of_week = start_date - timedelta(days=start_date.weekday())
    return [start_of_week + timedelta(days=i) for i in range(7)]


@login_required
@customer_required
def available_appointment(request, doctor_id, start_date=None):
    doctor = get_object_or_404(
        Doctor.objects.select_related('billing', 'user'),
        id=doctor_id
    )

    now = datetime.now()
    start_date = now.date() if not start_date else datetime.strptime(start_date, "%Y-%m-%d").date()

    billing = getattr(doctor, 'billing', None)

    consultation_fee = Decimal('0.00')
    esewa_number = ''
    esewa_enabled = False
    mediconnect_percentage = Decimal('10.00')

    if billing:
        consultation_fee = Decimal(str(billing.consultation_fee or 0)).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )
        esewa_number = billing.esewa_number or ''
        esewa_enabled = billing.esewa_enabled

    mediconnect_fee = (
        (consultation_fee * mediconnect_percentage) / Decimal('100')
    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    total_amount = (
        consultation_fee + mediconnect_fee
    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    available_payment_methods = ['cash']
    if esewa_enabled and esewa_number:
        available_payment_methods.append('esewa')

    existing_active_appointment = Appointment.objects.filter(
        patient=request.user,
        doctor=doctor,
        appointment_status__in=['pending', 'confirmed']
    ).order_by('-id').first()

    week_dates = [start_date + timedelta(days=i) for i in range(7)]

    time_slots = {}
    for date in week_dates:
        day_name = date.strftime("%A").lower()

        slots = TimeSlot.objects.filter(
            doctor=doctor,
            day=date.strftime("%A"),
            availability=True
        ).order_by('start_time')

        time_slots[day_name] = []

        for slot in slots:
            slot_time = datetime.combine(date, slot.start_time)

            is_booked = Booking.objects.filter(
                time_slot=slot,
                date=date
            ).exists()

            if slot_time < now + timedelta(hours=2):
                is_booked = True

            time_slots[day_name].append({
                'slot': slot,
                'is_booked': is_booked
            })

    context = {
        'current_date': now.strftime('%Y-%m-%d'),
        'doctor': doctor,
        'time_slots': time_slots,
        'week_dates': week_dates,
        'billing': billing,
        'consultation_fee': consultation_fee,
        'esewa_number': esewa_number,
        'esewa_enabled': esewa_enabled,
        'mediconnect_percentage': mediconnect_percentage,
        'mediconnect_fee': mediconnect_fee,
        'total_amount': total_amount,
        'available_payment_methods': available_payment_methods,
        'existing_active_appointment': existing_active_appointment,
    }

    return render(request, 'customers/booking.html', context)


@login_required
@customer_required
def appointment_details(request, appointment_id):
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
        patient=request.user
    )

    latest_remark = appointment.remarks.first()
    remark_medicines = latest_remark.medicines.all() if latest_remark else []

    return render(request, 'customers/appointment_details.html', {
        'appointment': appointment,
        'latest_remark': latest_remark,
        'remark_medicines': remark_medicines,
    })


@login_required
def payment_history(request):
    payments = Payment.objects.select_related(
        'doctor',
        'doctor__user',
        'appointment'
    ).filter(
        patient=request.user
    ).order_by('-created_at')

    context = {
        'payments': payments
    }
    return render(request, 'customers/payment_history.html', context)


@login_required
@customer_required
def download_prescription_pdf(request, appointment_id):
    import re
    from xml.sax.saxutils import escape

    appointment = get_object_or_404(
        Appointment.objects.select_related(
            'doctor',
            'doctor__user',
            'patient',
            'time_slot',
        ).prefetch_related(
            Prefetch(
                'remarks',
                queryset=Remark.objects.select_related(
                    'doctor',
                    'doctor__user',
                ).prefetch_related(
                    Prefetch(
                        'medicines',
                        queryset=RemarkMedicine.objects.select_related('medicine')
                    )
                ).order_by('-created_at')
            )
        ),
        pk=appointment_id,
        patient=request.user
    )

    latest_remark = appointment.remarks.first()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{appointment.id}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]

    body_style.fontName = "Helvetica"
    body_style.fontSize = 10
    body_style.leading = 14
    body_style.wordWrap = 'CJK'

    label_style = styles["BodyText"].clone("label_style")
    label_style.fontName = "Helvetica-Bold"
    label_style.fontSize = 10
    label_style.leading = 14
    label_style.wordWrap = 'CJK'

    cell_style = styles["BodyText"].clone("cell_style")
    cell_style.fontName = "Helvetica"
    cell_style.fontSize = 10
    cell_style.leading = 14
    cell_style.wordWrap = 'CJK'

    header_cell_style = styles["BodyText"].clone("header_cell_style")
    header_cell_style.fontName = "Helvetica-Bold"
    header_cell_style.fontSize = 10
    header_cell_style.leading = 14
    header_cell_style.wordWrap = 'CJK'

    def clean_text(value):
        if not value:
            return "N/A"

        text = str(value)

        replacements = {
            "■": "- ",
            "▪": "- ",
            "●": "- ",
            "•": "- ",
            "◦": "- ",
            "\r\n": "\n",
            "\r": "\n",
            "\t": " ",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace("\n", "<br/>")
        return text

    def p(text, style=cell_style):
        return Paragraph(clean_text(text), style)

    story = []

    story.append(Paragraph("Medical Prescription", title_style))
    story.append(Spacer(1, 12))

    patient_name = "N/A"
    if appointment.patient:
        patient_name = f"{appointment.patient.first_name} {appointment.patient.last_name}".strip()
        if not patient_name:
            patient_name = appointment.patient.username or appointment.patient.email

    doctor_name = "N/A"
    if appointment.doctor and appointment.doctor.user:
        doctor_name = f"{appointment.doctor.user.first_name} {appointment.doctor.user.last_name}".strip()
        if not doctor_name:
            doctor_name = appointment.doctor.user.username or appointment.doctor.user.email

    appointment_date = appointment.appointment_date.strftime("%Y-%m-%d") if appointment.appointment_date else "N/A"

    slot_time = "N/A"
    if appointment.time_slot:
        start_time = appointment.time_slot.start_time.strftime("%I:%M %p") if appointment.time_slot.start_time else ""
        end_time = appointment.time_slot.end_time.strftime("%I:%M %p") if appointment.time_slot.end_time else ""
        slot_time = f"{start_time} - {end_time}".strip(" -")

    info_data = [
        [Paragraph("Appointment ID", label_style), p(str(appointment.id))],
        [Paragraph("Patient Name", label_style), p(patient_name)],
        [Paragraph("Doctor Name", label_style), p(doctor_name)],
        [Paragraph("Appointment Date", label_style), p(appointment_date)],
        [Paragraph("Time Slot", label_style), p(slot_time)],
        [Paragraph("Appointment Type", label_style), p(appointment.appointment_type or "N/A")],
        [Paragraph("Status", label_style), p(appointment.appointment_status or "N/A")],
    ]

    info_table = Table(info_data, colWidths=[60 * mm, 115 * mm])
    info_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(info_table)
    story.append(Spacer(1, 16))

    if latest_remark:
        story.append(Paragraph("Doctor Remark", heading_style))
        story.append(Spacer(1, 6))

        diagnosis = getattr(latest_remark, "diagnosis", "") or "N/A"
        symptoms = getattr(latest_remark, "symptoms", "") or "N/A"
        note = getattr(latest_remark, "note", "") or "N/A"
        advice = getattr(latest_remark, "advice", "") or "N/A"
        follow_up_date = getattr(latest_remark, "follow_up_date", None)
        follow_up_date = follow_up_date.strftime("%Y-%m-%d") if follow_up_date else "N/A"

        remark_data = [
            [Paragraph("Diagnosis", label_style), p(diagnosis)],
            [Paragraph("Symptoms", label_style), p(symptoms)],
            [Paragraph("Note", label_style), p(note)],
            [Paragraph("Advice", label_style), p(advice)],
            [Paragraph("Follow Up Date", label_style), p(follow_up_date)],
        ]

        remark_table = Table(remark_data, colWidths=[60 * mm, 115 * mm])
        remark_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))

        story.append(remark_table)
        story.append(Spacer(1, 16))

        story.append(Paragraph("Prescribed Medicines", heading_style))
        story.append(Spacer(1, 6))

        medicines = latest_remark.medicines.all()

        if medicines.exists():
            medicine_rows = [[
                Paragraph("Medicine", header_cell_style),
                Paragraph("Dosage", header_cell_style),
                Paragraph("Qty", header_cell_style),
                Paragraph("Frequency", header_cell_style),
                Paragraph("Duration", header_cell_style),
                Paragraph("Instruction", header_cell_style),
            ]]

            for med in medicines:
                medicine_name = str(med.medicine) if med.medicine else "N/A"
                dosage = getattr(med, "dosage", "") or "N/A"
                quantity = getattr(med, "quantity", "") or "N/A"
                frequency = getattr(med, "frequency", "") or "N/A"
                duration = getattr(med, "duration", "") or "N/A"
                instruction = getattr(med, "instruction", "") or "N/A"

                medicine_rows.append([
                    p(medicine_name),
                    p(dosage),
                    p(str(quantity)),
                    p(frequency),
                    p(duration),
                    p(instruction),
                ])

            medicine_table = Table(
                medicine_rows,
                colWidths=[35 * mm, 22 * mm, 15 * mm, 30 * mm, 22 * mm, 51 * mm],
                repeatRows=1
            )
            medicine_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(medicine_table)
        else:
            story.append(Paragraph("No medicines prescribed.", body_style))
    else:
        story.append(Paragraph("No doctor remark has been added yet for this appointment.", body_style))

    story.append(Spacer(1, 20))
    story.append(Paragraph("Generated from MediConnect system.", body_style))

    doc.build(story)
    return response