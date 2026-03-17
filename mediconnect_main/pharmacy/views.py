from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from appointment.models import Appointment
from doctor.models import Doctor

from accounts.models import User

from .forms import MedicineForm, PrescriptionForm, PrescriptionItemFormSet
from .models import Medicine, Prescription, DispenseRecord


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
def medicine_create(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST,request.FILES)
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
        form = MedicineForm(request.POST,request.FILES, instance=med)
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

    # Check stock
    for item in rx.items.select_related('medicine').all():
        if item.medicine.stock_qty < item.quantity:
            messages.error(request, f"Not enough stock for {item.medicine}. Available: {item.medicine.stock_qty}")
            return redirect('pharmacy_prescription_detail', pk=pk)

    # Deduct stock
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

    # Safety: ensure the appointment belongs to this doctor
    if appointment.doctor_id != doctor.id:
        raise PermissionDenied

    rx, _ = Prescription.objects.get_or_create(
        appointment=appointment,
        defaults={'doctor': doctor, 'patient': appointment.patient}
    )

    if request.method == 'POST':
        form = PrescriptionForm(request.POST,request.FILES, instance=rx)
        formset = PrescriptionItemFormSet(request.POST,request.FILES, instance=rx)
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
