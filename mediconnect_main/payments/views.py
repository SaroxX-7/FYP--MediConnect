import base64
import hashlib
import hmac
import io
import json
import uuid

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from doctor.models import Payment


def generate_signature(message: str, secret_key: str) -> str:
    digest = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode()


def verify_signature(message: str, secret_key: str, received_signature: str) -> bool:
    expected_signature = generate_signature(message, secret_key)
    return hmac.compare_digest(expected_signature, received_signature)


def build_appointment_invoice_pdf(payment):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    story = []

    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]

    appointment = payment.appointment
    patient = payment.patient
    doctor = payment.doctor

    patient_name = "N/A"
    if patient:
        patient_name = f"{patient.first_name} {patient.last_name}".strip()
        if not patient_name:
            patient_name = patient.username or patient.email

    doctor_name = "N/A"
    if doctor and doctor.user:
        doctor_name = f"Dr. {doctor.user.first_name} {doctor.user.last_name}".strip()
        if doctor_name == "Dr.":
            doctor_name = doctor.user.username or doctor.user.email

    appointment_date = (
        appointment.appointment_date.strftime("%Y-%m-%d")
        if appointment and appointment.appointment_date else "N/A"
    )

    slot_time = "N/A"
    if appointment and appointment.time_slot:
        start_time = appointment.time_slot.start_time.strftime("%I:%M %p") if appointment.time_slot.start_time else ""
        end_time = appointment.time_slot.end_time.strftime("%I:%M %p") if appointment.time_slot.end_time else ""
        slot_time = f"{start_time} - {end_time}".strip(" -")

    story.append(Paragraph("MediConnect Appointment Invoice", title_style))
    story.append(Spacer(1, 12))

    info_data = [
        ["Invoice For", "Doctor Appointment Booking"],
        ["Payment ID", str(payment.id)],
        ["Patient Name", patient_name],
        ["Doctor Name", doctor_name],
        ["Appointment Date", appointment_date],
        ["Time Slot", slot_time],
        ["Appointment Type", appointment.appointment_type if appointment else "N/A"],
        ["Payment Method", payment.payment_method or "N/A"],
        ["Payment Status", payment.payment_status or "N/A"],
        ["Transaction ID", payment.transaction_id or payment.transaction_uuid or "N/A"],
    ]

    info_table = Table(info_data, colWidths=[55 * mm, 120 * mm])
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

    story.append(Paragraph("Payment Breakdown", heading_style))
    story.append(Spacer(1, 8))

    bill_data = [
        ["Description", "Amount"],
        ["Doctor Fee", f"Rs. {payment.doctor_fee}"],
        [f"MediConnect Fee ({payment.mediconnect_percentage}%)", f"Rs. {payment.mediconnect_fee}"],
        ["Total Amount", f"Rs. {payment.total_amount}"],
    ]

    bill_table = Table(bill_data, colWidths=[120 * mm, 55 * mm])
    bill_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(bill_table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Thank you for booking with MediConnect.", body_style))
    story.append(Paragraph("Please keep this invoice for your records.", body_style))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def send_appointment_invoice_email(payment):
    patient = payment.patient
    appointment = payment.appointment
    doctor = payment.doctor

    if not patient or not patient.email:
        return

    patient_name = f"{patient.first_name} {patient.last_name}".strip()
    if not patient_name:
        patient_name = patient.username

    doctor_name = "N/A"
    if doctor and doctor.user:
        doctor_name = f"Dr. {doctor.user.first_name} {doctor.user.last_name}".strip()
        if doctor_name == "Dr.":
            doctor_name = doctor.user.username or doctor.user.email

    appointment_date = (
        appointment.appointment_date.strftime("%Y-%m-%d")
        if appointment and appointment.appointment_date else "N/A"
    )

    slot_time = "N/A"
    if appointment and appointment.time_slot:
        start_time = appointment.time_slot.start_time.strftime("%I:%M %p") if appointment.time_slot.start_time else ""
        end_time = appointment.time_slot.end_time.strftime("%I:%M %p") if appointment.time_slot.end_time else ""
        slot_time = f"{start_time} - {end_time}".strip(" -")

    text_content = f"""
MediConnect Appointment Receipt

Patient: {patient_name}
Doctor: {doctor_name}
Appointment Date: {appointment_date}
Time Slot: {slot_time}
Payment Method: {payment.payment_method}
Payment Status: {payment.payment_status}

Doctor Fee: Rs. {payment.doctor_fee}
MediConnect Fee: Rs. {payment.mediconnect_fee}
Total Amount: Rs. {payment.total_amount}

Thank you for using MediConnect.
""".strip()

    html_content = f"""
    <div style="font-family:Arial,sans-serif; background:#f4f6f8; padding:30px;">
        <div style="max-width:700px; margin:0 auto; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 4px 12px rgba(0,0,0,0.08);">
            <div style="background:linear-gradient(135deg,#2563eb,#1d4ed8); color:white; padding:24px;">
                <h2 style="margin:0;">MediConnect Appointment Receipt</h2>
                <p style="margin:6px 0 0;">Payment #{payment.id}</p>
            </div>

            <div style="padding:24px;">
                <p><strong>Patient:</strong> {patient_name}</p>
                <p><strong>Doctor:</strong> {doctor_name}</p>
                <p><strong>Appointment Date:</strong> {appointment_date}</p>
                <p><strong>Time Slot:</strong> {slot_time}</p>
                <p><strong>Payment Method:</strong> {payment.payment_method}</p>
                <p><strong>Payment Status:</strong> {payment.payment_status}</p>

                <h3 style="margin-top:30px; color:#1e293b;">Payment Breakdown</h3>

                <table style="width:100%; border-collapse:collapse; margin-top:10px;">
                    <thead>
                        <tr style="background:#f1f5f9;">
                            <th style="padding:10px; border:1px solid #ddd; text-align:left;">Description</th>
                            <th style="padding:10px; border:1px solid #ddd; text-align:right;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding:10px; border:1px solid #ddd;">Doctor Fee</td>
                            <td style="padding:10px; border:1px solid #ddd; text-align:right;">Rs. {payment.doctor_fee}</td>
                        </tr>
                        <tr>
                            <td style="padding:10px; border:1px solid #ddd;">MediConnect Fee ({payment.mediconnect_percentage}%)</td>
                            <td style="padding:10px; border:1px solid #ddd; text-align:right;">Rs. {payment.mediconnect_fee}</td>
                        </tr>
                        <tr>
                            <td style="padding:10px; border:1px solid #ddd; font-weight:bold;">Total Amount</td>
                            <td style="padding:10px; border:1px solid #ddd; text-align:right; font-weight:bold; color:#2563eb;">Rs. {payment.total_amount}</td>
                        </tr>
                    </tbody>
                </table>

                <hr style="margin:30px 0; border:none; border-top:1px solid #e5e7eb;">

                <p style="margin:0; color:#475569;">Thank you for booking with <strong>MediConnect</strong>.</p>
            </div>
        </div>
    </div>
    """

    pdf_content = build_appointment_invoice_pdf(payment)

    email = EmailMultiAlternatives(
        subject=f"MediConnect Appointment Invoice - Payment #{payment.id}",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[patient.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.attach(
        f"mediconnect_appointment_invoice_{payment.id}.pdf",
        pdf_content,
        "application/pdf"
    )
    email.send(fail_silently=False)


@login_required
def initiate_payment(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('appointment', 'doctor', 'patient'),
        id=payment_id,
        patient=request.user,
        payment_method='esewa'
    )

    if payment.payment_status == 'paid':
        messages.info(request, "This payment is already completed.")
        return redirect('appointment_details', appointment_id=payment.appointment.id)

    transaction_uuid = f"APT-{payment.appointment.id}-{uuid.uuid4().hex[:10]}"
    payment.transaction_uuid = transaction_uuid
    payment.payment_status = 'pending'
    payment.save(update_fields=['transaction_uuid', 'payment_status', 'updated_at'])

    total_amount = str(payment.total_amount)
    product_code = settings.ESEWA_MERCHANT_ID

    message_to_sign = (
        f"total_amount={total_amount},"
        f"transaction_uuid={transaction_uuid},"
        f"product_code={product_code}"
    )
    signature = generate_signature(message_to_sign, settings.ESEWA_SECRET_KEY)

    success_url = request.build_absolute_uri('/payments/success/')
    failure_url = request.build_absolute_uri(f'/payments/failure/?payment_id={payment.id}')

    context = {
        "payment": payment,
        "payment_url": settings.ESEWA_PAYMENT_URL,
        "amount": total_amount,
        "tax_amount": "0",
        "total_amount": total_amount,
        "transaction_uuid": transaction_uuid,
        "product_code": product_code,
        "product_service_charge": "0",
        "product_delivery_charge": "0",
        "success_url": success_url,
        "failure_url": failure_url,
        "signed_field_names": "total_amount,transaction_uuid,product_code",
        "signature": signature,
    }
    return render(request, "payments/esewa_form.html", context)


@login_required
def payment_success(request):
    encoded_data = request.GET.get('data')

    if not encoded_data:
        messages.error(request, "Missing payment response from eSewa.")
        return redirect('customer')

    try:
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_data = json.loads(decoded_bytes.decode('utf-8'))
    except Exception:
        messages.error(request, "Invalid payment response received.")
        return redirect('customer')

    transaction_uuid = decoded_data.get('transaction_uuid')
    total_amount = str(decoded_data.get('total_amount'))
    status = decoded_data.get('status')
    product_code = decoded_data.get('product_code')
    received_signature = decoded_data.get('signature')
    signed_field_names = decoded_data.get('signed_field_names', '')
    transaction_code = decoded_data.get('transaction_code')

    payment = get_object_or_404(
        Payment.objects.select_related('appointment', 'appointment__time_slot', 'doctor', 'doctor__user', 'patient'),
        transaction_uuid=transaction_uuid,
        patient=request.user
    )

    signed_values = []
    for field in signed_field_names.split(','):
        field = field.strip()
        if field in decoded_data:
            signed_values.append(f"{field}={decoded_data[field]}")
    signed_message = ",".join(signed_values)

    if received_signature and not verify_signature(
        signed_message,
        settings.ESEWA_SECRET_KEY,
        received_signature
    ):
        payment.payment_status = 'failed'
        payment.save(update_fields=['payment_status', 'updated_at'])
        messages.error(request, "Payment signature verification failed.")
        return redirect('appointment_details', appointment_id=payment.appointment.id)

    try:
        response = requests.get(
            settings.ESEWA_STATUS_URL,
            params={
                'product_code': product_code,
                'total_amount': total_amount,
                'transaction_uuid': transaction_uuid,
            },
            timeout=15
        )
        response.raise_for_status()
        status_data = response.json()
    except Exception:
        messages.warning(
            request,
            "Payment returned successfully, but server verification could not be completed. Please check again."
        )
        return redirect('appointment_details', appointment_id=payment.appointment.id)

    verified_status = status_data.get('status')
    ref_id = status_data.get('ref_id')

    if status == 'COMPLETE' and verified_status == 'COMPLETE':
        payment.payment_status = 'paid'
        payment.transaction_id = ref_id or transaction_code
        payment.payment_date = timezone.now()
        payment.save(update_fields=['payment_status', 'transaction_id', 'payment_date', 'updated_at'])

        try:
            send_appointment_invoice_email(payment)
        except Exception as e:
            print(f"Appointment invoice email failed: {e}")

        messages.success(request, "Payment completed successfully. Invoice has been sent to your email.")
    else:
        payment.payment_status = 'failed'
        payment.save(update_fields=['payment_status', 'updated_at'])
        messages.error(request, "Payment was not completed.")

    return redirect('appointment_details', appointment_id=payment.appointment.id)


@login_required
def payment_failure(request):
    payment_id = request.GET.get('payment_id')

    if payment_id:
        try:
            payment = Payment.objects.select_related('appointment', 'patient').get(
                id=payment_id,
                patient=request.user
            )
            if payment.payment_status != 'paid':
                payment.payment_status = 'failed'
                payment.save(update_fields=['payment_status', 'updated_at'])
            messages.error(request, "Payment failed or was cancelled.")
            return redirect('appointment_details', appointment_id=payment.appointment.id)
        except Payment.DoesNotExist:
            pass

    messages.error(request, "Payment failed or was cancelled.")
    return redirect('customer')