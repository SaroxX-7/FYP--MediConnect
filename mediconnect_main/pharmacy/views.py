import base64
import hashlib
import hmac
import io
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

from accounts.models import User
from appointment.models import Appointment, Remark
from doctor.models import Doctor

from .forms import MedicineForm, PrescriptionForm, PrescriptionItemFormSet
from .models import Medicine, Prescription, DispenseRecord, PharmacyOrder, PharmacyOrderItem


def check_role_pharmacist(user):
    if getattr(user, 'role', None) == User.PHARMACIST:
        return True
    raise PermissionDenied


def check_role_doctor(user):
    if getattr(user, 'role', None) == User.DOCTOR:
        return True
    raise PermissionDenied


def check_role_customer(user):
    if getattr(user, 'role', None) == User.CUSTOMER:
        return True
    raise PermissionDenied


@login_required(login_url='login')
@user_passes_test(check_role_pharmacist)
def pharmacist_dashboard(request):
    medicines = Medicine.objects.all()
    prescriptions = Prescription.objects.select_related('patient', 'doctor').all()[:20]
    context = {
        'medicines': medicines,
        'prescriptions': prescriptions,
    }
    return render(request, 'pharmacy/pharmacist_dashboard.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_pharmacist)
def pharmacist_profile(request):
    context = {
        'user': request.user,
    }
    return render(request, 'pharmacy/pharmacist_profile.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_pharmacist)
def medicine_create(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine added.')
            return redirect('pharmacist_dashboard')
    else:
        form = MedicineForm()
    return render(request, 'pharmacy/medicine_form.html', {'form': form, 'title': 'Add Medicine'})


@login_required(login_url='login')
@user_passes_test(check_role_pharmacist)
def medicine_edit(request, pk):
    med = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        form = MedicineForm(request.POST, request.FILES, instance=med)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine updated.')
            return redirect('pharmacist_dashboard')
    else:
        form = MedicineForm(instance=med)
    return render(request, 'pharmacy/medicine_form.html', {'form': form, 'title': 'Edit Medicine'})


@login_required(login_url='login')
@user_passes_test(check_role_pharmacist)
def prescription_detail(request, pk):
    rx = get_object_or_404(Prescription, pk=pk)
    return render(request, 'pharmacy/prescription_detail.html', {'rx': rx})


@login_required(login_url='login')
@user_passes_test(check_role_pharmacist)
@transaction.atomic
def dispense_prescription(request, pk):
    rx = get_object_or_404(Prescription, pk=pk)

    if rx.status == 'dispensed':
        messages.info(request, 'This prescription is already dispensed.')
        return redirect('pharmacy_prescription_detail', pk=pk)

    for item in rx.items.select_related('medicine').all():
        if item.medicine.stock_qty < item.quantity:
            messages.error(request, f"Not enough stock for {item.medicine}. Available: {item.medicine.stock_qty}")
            return redirect('pharmacy_prescription_detail', pk=pk)

    for item in rx.items.select_related('medicine').all():
        med = item.medicine
        med.stock_qty = med.stock_qty - item.quantity
        med.save(update_fields=['stock_qty'])

    rx.status = 'dispensed'
    rx.save(update_fields=['status'])

    DispenseRecord.objects.get_or_create(
        prescription=rx,
        defaults={'pharmacist': request.user}
    )

    messages.success(request, 'Prescription dispensed and stock updated.')
    return redirect('pharmacy_prescription_detail', pk=pk)


@login_required(login_url='login')
@user_passes_test(check_role_doctor)
def doctor_prescription_for_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    doctor = get_object_or_404(Doctor, user=request.user)

    if appointment.doctor_id != doctor.id:
        raise PermissionDenied

    rx, _ = Prescription.objects.get_or_create(
        appointment=appointment,
        defaults={'doctor': doctor, 'patient': appointment.patient}
    )

    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request.FILES, instance=rx)
        formset = PrescriptionItemFormSet(request.POST, request.FILES, instance=rx)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Prescription saved.')
            return redirect('appointment_details', appointment_id=appointment_id)
    else:
        form = PrescriptionForm(instance=rx)
        formset = PrescriptionItemFormSet(instance=rx)

    return render(request, 'pharmacy/doctor_prescription_form.html', {
        'appointment': appointment,
        'form': form,
        'formset': formset,
        'rx': rx,
    })


@login_required(login_url='login')
@user_passes_test(check_role_customer)
def patient_prescriptions(request):
    rxs = Prescription.objects.filter(patient=request.user).select_related('doctor').prefetch_related('items__medicine')
    return render(request, 'pharmacy/patient_prescriptions.html', {'rxs': rxs})


@login_required(login_url='login')
def pharmacy_store(request):
    medicines = Medicine.objects.all().order_by('name')

    context = {
        'medicines': medicines,
    }
    return render(request, 'pharmacy/pharmacy_store.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_customer)
def add_to_cart(request, medicine_id):
    medicine = get_object_or_404(Medicine, pk=medicine_id)

    if request.method != 'POST':
        return redirect('pharmacy_store')

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        messages.error(request, "Invalid quantity.")
        return redirect('pharmacy_store')

    if quantity < 1:
        messages.error(request, "Quantity must be at least 1.")
        return redirect('pharmacy_store')

    if medicine.stock_qty < quantity:
        messages.error(request, f"Only {medicine.stock_qty} items available for {medicine.name}.")
        return redirect('pharmacy_store')

    cart = request.session.get('cart', {})
    medicine_id_str = str(medicine.id)

    cart[medicine_id_str] = cart.get(medicine_id_str, 0) + quantity
    request.session['cart'] = cart

    medicine.stock_qty -= quantity
    medicine.save(update_fields=['stock_qty'])

    messages.success(request, f"{quantity} x {medicine.name} added to cart.")
    return redirect('pharmacy_store')


@login_required(login_url='login')
@user_passes_test(check_role_customer)
def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = Decimal('0.00')

    for medicine_id, quantity in cart.items():
        medicine = get_object_or_404(Medicine, pk=medicine_id)
        quantity = int(quantity)
        subtotal = medicine.unit_price * quantity
        total += subtotal

        cart_items.append({
            'medicine': medicine,
            'quantity': quantity,
            'subtotal': subtotal,
        })

    context = {
        'cart_items': cart_items,
        'total': total,
    }
    return render(request, 'pharmacy/cart.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_customer)
def remove_from_cart(request, medicine_id):
    cart = request.session.get('cart', {})
    medicine_id_str = str(medicine_id)

    if medicine_id_str in cart:
        quantity = cart[medicine_id_str]
        medicine = get_object_or_404(Medicine, pk=medicine_id)

        medicine.stock_qty += quantity
        medicine.save(update_fields=['stock_qty'])

        del cart[medicine_id_str]
        request.session['cart'] = cart

        messages.success(request, f"{medicine.name} removed from cart and {quantity} item(s) restored to stock.")
    else:
        messages.error(request, "Medicine not found in cart.")

    return redirect('view_cart')


@login_required(login_url='login')
@user_passes_test(check_role_customer)
def add_remark_medicines_to_cart(request, remark_id):
    if request.method != 'POST':
        return redirect('home')

    remark = get_object_or_404(
        Remark.objects.select_related('appointment', 'appointment__patient').prefetch_related('medicines__medicine'),
        pk=remark_id
    )

    if remark.appointment.patient != request.user:
        raise PermissionDenied

    remark_medicines = remark.medicines.select_related('medicine').all()

    if not remark_medicines.exists():
        messages.error(request, "No medicines found in this remark.")
        return redirect('appointment_details', appointment_id=remark.appointment.id)

    for item in remark_medicines:
        if item.medicine.stock_qty < item.quantity:
            messages.error(
                request,
                f"Not enough stock for {item.medicine.name}. Available: {item.medicine.stock_qty}, required: {item.quantity}"
            )
            return redirect('appointment_details', appointment_id=remark.appointment.id)

    cart = request.session.get('cart', {})

    for item in remark_medicines:
        medicine = item.medicine
        medicine_id_str = str(medicine.id)

        cart[medicine_id_str] = cart.get(medicine_id_str, 0) + item.quantity

        medicine.stock_qty -= item.quantity
        medicine.save(update_fields=['stock_qty'])

    request.session['cart'] = cart

    messages.success(request, "All medicines from the doctor remark were added to your cart.")
    return redirect('view_cart')


@login_required(login_url='login')
@user_passes_test(check_role_customer)
def cart_checkout_esewa(request):
    cart = request.session.get('cart', {})

    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('view_cart')

    total = Decimal('0.00')

    for medicine_id, quantity in cart.items():
        medicine = get_object_or_404(Medicine, pk=medicine_id)
        quantity = int(quantity)
        subtotal = medicine.unit_price * quantity
        total += subtotal

    transaction_uuid = str(uuid.uuid4())
    product_code = settings.ESEWA_MERCHANT_ID

    message = f"total_amount={total},transaction_uuid={transaction_uuid},product_code={product_code}"
    signature = base64.b64encode(
        hmac.new(
            settings.ESEWA_SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
    ).decode()

    request.session['cart_checkout_transaction_uuid'] = transaction_uuid
    request.session['cart_checkout_total'] = str(total)

    context = {
        'payment_url': settings.ESEWA_PAYMENT_URL,
        'amount': total,
        'tax_amount': Decimal('0.00'),
        'total_amount': total,
        'transaction_uuid': transaction_uuid,
        'product_code': product_code,
        'product_service_charge': Decimal('0.00'),
        'product_delivery_charge': Decimal('0.00'),
        'success_url': request.build_absolute_uri('/pharmacy/cart/checkout/success/'),
        'failure_url': request.build_absolute_uri('/pharmacy/cart/checkout/failure/'),
        'signed_field_names': 'total_amount,transaction_uuid,product_code',
        'signature': signature,
    }

    return render(request, 'payments/esewa_form.html', context)


def build_pharmacy_invoice_pdf(pharmacy_order, customer_name, customer_email, transaction_uuid, items_data, total):
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

    story.append(Paragraph("MediConnect Pharmacy Invoice", title_style))
    story.append(Spacer(1, 10))

    info_data = [
        ["Order ID", f"#{pharmacy_order.id}"],
        ["Customer", customer_name],
        ["Email", customer_email or "N/A"],
        ["Transaction ID", transaction_uuid or "N/A"],
        ["Order Date", timezone.now().strftime('%Y-%m-%d %H:%M:%S')],
        ["Payment Method", "eSewa"],
        ["Payment Status", "Paid"],
    ]

    info_table = Table(info_data, colWidths=[45 * mm, 130 * mm])
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

    story.append(Paragraph("Purchased Medicines", heading_style))
    story.append(Spacer(1, 8))

    medicine_rows = [["Medicine", "Qty", "Unit Price", "Subtotal"]]
    for item in items_data:
        medicine_rows.append([
            item["name"],
            str(item["quantity"]),
            f"Rs. {item['unit_price']}",
            f"Rs. {item['subtotal']}",
        ])

    medicine_rows.append(["", "", "Total Amount", f"Rs. {total}"])

    medicine_table = Table(medicine_rows, colWidths=[80 * mm, 20 * mm, 35 * mm, 40 * mm])
    medicine_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(medicine_table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Thank you for using MediConnect Pharmacy.", body_style))
    story.append(Paragraph("For any queries, please contact support@mediconnect.com", body_style))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


@login_required(login_url='login')
@user_passes_test(check_role_customer)
@transaction.atomic
def cart_checkout_success(request):
    cart = request.session.get('cart', {})
    transaction_uuid = request.session.get('cart_checkout_transaction_uuid')
    cart_total = request.session.get('cart_checkout_total')

    if not cart:
        messages.success(request, "Payment successful.")
        return redirect('pharmacy_store')

    total = Decimal('0.00')
    customer_name = f"{request.user.first_name} {request.user.last_name}".strip()
    if not customer_name:
        customer_name = request.user.username

    pharmacy_order = PharmacyOrder.objects.create(
        customer=request.user,
        transaction_uuid=transaction_uuid,
        payment_method='esewa',
        payment_status='paid',
        total_amount=Decimal(cart_total) if cart_total else Decimal('0.00')
    )

    items_html = ""
    items_data = []
    receipt_lines = [
        "=" * 50,
        "MediConnect Pharmacy Receipt",
        "=" * 50,
        f"Customer: {customer_name}",
        f"Email: {request.user.email}",
        f"Transaction ID: {transaction_uuid or 'N/A'}",
        f"Order ID: #{pharmacy_order.id}",
        f"Order Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "-" * 50,
        "Medicines Purchased:",
        "-" * 50,
    ]

    for medicine_id, quantity in cart.items():
        medicine = get_object_or_404(Medicine, pk=medicine_id)
        quantity = int(quantity)
        unit_price = medicine.unit_price
        subtotal = unit_price * quantity
        total += subtotal

        PharmacyOrderItem.objects.create(
            order=pharmacy_order,
            medicine=medicine,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal
        )

        items_data.append({
            "name": medicine.name,
            "quantity": quantity,
            "unit_price": unit_price,
            "subtotal": subtotal,
        })

        receipt_lines.append(
            f"{medicine.name} | Qty: {quantity} | Unit: Rs. {unit_price} | Subtotal: Rs. {subtotal}"
        )

        items_html += f"""
            <tr>
                <td style="padding:10px; border:1px solid #ddd;">{medicine.name}</td>
                <td style="padding:10px; border:1px solid #ddd; text-align:center;">{quantity}</td>
                <td style="padding:10px; border:1px solid #ddd; text-align:right;">Rs. {unit_price}</td>
                <td style="padding:10px; border:1px solid #ddd; text-align:right;">Rs. {subtotal}</td>
            </tr>
        """

    pharmacy_order.total_amount = total
    pharmacy_order.save(update_fields=['total_amount'])

    receipt_lines.extend([
        "",
        "-" * 50,
        f"Total Amount: Rs. {total}",
        "Payment Method: eSewa",
        "Payment Status: Paid",
        "-" * 50,
        "Thank you for using MediConnect Pharmacy.",
        "For any queries, please contact support@mediconnect.com",
        "=" * 50,
    ])

    if request.user.email:
        try:
            html_content = f"""
            <div style="font-family:Arial,sans-serif; background:#f4f6f8; padding:30px;">
                <div style="max-width:700px; margin:0 auto; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 4px 12px rgba(0,0,0,0.08);">

                    <div style="background:linear-gradient(135deg,#2563eb,#1d4ed8); color:white; padding:24px;">
                        <h2 style="margin:0;">MediConnect Pharmacy Receipt</h2>
                        <p style="margin:6px 0 0;">Order #{pharmacy_order.id}</p>
                    </div>

                    <div style="padding:24px;">
                        <p><strong>Customer:</strong> {customer_name}</p>
                        <p><strong>Email:</strong> {request.user.email}</p>
                        <p><strong>Transaction ID:</strong> {transaction_uuid or 'N/A'}</p>
                        <p><strong>Order Date:</strong> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

                        <h3 style="margin-top:30px; color:#1e293b;">Purchased Medicines</h3>

                        <table style="width:100%; border-collapse:collapse; margin-top:10px;">
                            <thead>
                                <tr style="background:#f1f5f9;">
                                    <th style="padding:10px; border:1px solid #ddd; text-align:left;">Medicine</th>
                                    <th style="padding:10px; border:1px solid #ddd; text-align:center;">Qty</th>
                                    <th style="padding:10px; border:1px solid #ddd; text-align:right;">Unit Price</th>
                                    <th style="padding:10px; border:1px solid #ddd; text-align:right;">Subtotal</th>
                                </tr>
                            </thead>
                            <tbody>
                                {items_html}
                            </tbody>
                        </table>

                        <div style="margin-top:25px; text-align:right;">
                            <p style="font-size:18px; margin:0;"><strong>Total Amount:</strong>
                                <span style="color:#2563eb;">Rs. {total}</span>
                            </p>
                            <p style="margin:8px 0 0;"><strong>Payment Method:</strong> eSewa</p>
                            <p style="margin:4px 0 0;"><strong>Payment Status:</strong> Paid</p>
                        </div>

                        <hr style="margin:30px 0; border:none; border-top:1px solid #e5e7eb;">

                        <p style="margin:0; color:#475569;">Thank you for using <strong>MediConnect Pharmacy</strong>.</p>
                        <p style="margin:8px 0 0; color:#64748b;">For support, contact support@mediconnect.com</p>
                    </div>
                </div>
            </div>
            """

            text_content = "\n".join(receipt_lines)
            pdf_content = build_pharmacy_invoice_pdf(
                pharmacy_order=pharmacy_order,
                customer_name=customer_name,
                customer_email=request.user.email,
                transaction_uuid=transaction_uuid,
                items_data=items_data,
                total=total,
            )

            email = EmailMultiAlternatives(
                subject=f"MediConnect Pharmacy Receipt - Order #{pharmacy_order.id}",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.attach(
                f"mediconnect_invoice_order_{pharmacy_order.id}.pdf",
                pdf_content,
                "application/pdf"
            )
            email.send(fail_silently=False)

        except Exception as e:
            print(f"Email sending failed: {e}")

    request.session['cart'] = {}
    request.session.modified = True
    request.session.pop('cart_checkout_transaction_uuid', None)
    request.session.pop('cart_checkout_total', None)

    messages.success(
        request,
        f"Payment successful! Order #{pharmacy_order.id} has been placed. "
        "A receipt and PDF invoice have been sent to your email."
    )
    return redirect('pharmacy_store')


@login_required(login_url='login')
@user_passes_test(check_role_customer)
def cart_checkout_failure(request):
    messages.error(request, "Payment failed or was cancelled.")
    return redirect('view_cart')
