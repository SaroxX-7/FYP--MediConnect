from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.db.models import Q
from django.forms import modelform_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.utils import timezone

from accounts.models import User, Department, Disease
from customers.models import Patient
from doctor.models import Doctor, Payment
from appointment.models import Appointment, TimeSlot, Remark
from pharmacy.models import Prescription, PrescriptionItem, Medicine, DispenseRecord
from .utils import staff_required


def _paginate(request, qs, per_page=10):
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def dashboard_login(request):
    if request.user.is_authenticated and (
        getattr(request.user, 'is_staff', False)
        or getattr(request.user, 'is_admin', False)
        or getattr(request.user, 'is_superadmin', False)
    ):
        return redirect('dashboard:home')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, email=email, password=password)

        if user is None:
            messages.error(request, 'Invalid credentials.')
            return redirect('dashboard:login')

        if not (
            getattr(user, 'is_staff', False)
            or getattr(user, 'is_admin', False)
            or getattr(user, 'is_superadmin', False)
        ):
            messages.error(request, 'You are not allowed to access the dashboard.')
            return redirect('dashboard:login')

        auth_login(request, user)
        messages.success(request, 'Welcome to the dashboard.')
        return redirect('dashboard:home')

    return render(request, 'dashboard/login.html')


@staff_required
def dashboard_logout(request):
    auth_logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('dashboard:login')


@staff_required
def dashboard_home(request):
    today = timezone.now().date()

    recent_appointments = Appointment.objects.select_related(
        'doctor', 'doctor__user', 'patient', 'time_slot'
    ).order_by('-appointment_date', '-id')[:5]

    recent_prescriptions = Prescription.objects.select_related(
        'doctor', 'doctor__user', 'patient', 'appointment'
    ).order_by('-created_at')[:5]

    recent_doctors = Doctor.objects.select_related(
        'user', 'department'
    ).order_by('-created_at')[:5]

    context = {
        'user_count': User.objects.count(),
        'doctor_count': Doctor.objects.count(),
        'patient_count': Patient.objects.count(),
        'appointment_count': Appointment.objects.count(),
        'today_appointment_count': Appointment.objects.filter(appointment_date=today).count(),
        'pending_appointment_count': Appointment.objects.filter(appointment_status='pending').count(),
        'confirmed_appointment_count': Appointment.objects.filter(appointment_status='confirmed').count(),
        'cancelled_appointment_count': Appointment.objects.filter(appointment_status='cancelled').count(),
        'prescription_count': Prescription.objects.count(),
        'medicine_count': Medicine.objects.count(),
        'payment_count': Payment.objects.count(),
        'department_count': Department.objects.count(),
        'disease_count': Disease.objects.count(),
        'recent_appointments': recent_appointments,
        'recent_prescriptions': recent_prescriptions,
        'recent_doctors': recent_doctors,
    }
    return render(request, 'dashboard/home.html', context)


# ---------------- USERS ----------------

@staff_required
def user_list(request):
    q = request.GET.get('q', '').strip()

    qs = User.objects.all().order_by('-created_date')
    if q:
        qs = qs.filter(
            Q(email__icontains=q) |
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(phone_number__icontains=q)
        )

    page = _paginate(request, qs, 12)
    return render(request, 'dashboard/user_list.html', {'page': page, 'q': q})


@staff_required
def user_create(request):
    Form = modelform_factory(
        User,
        fields=[
            'first_name', 'last_name', 'username', 'email',
            'phone_number', 'role', 'is_active',
            'is_staff', 'is_admin', 'is_superadmin'
        ]
    )

    if request.method == 'POST':
        form = Form(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            pwd = request.POST.get('password') or 'ChangeMe123!'
            user.set_password(pwd)
            user.save()
            messages.success(request, 'User created successfully.')
            return redirect('dashboard:user_list')
    else:
        form = Form()

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Create User',
        'subtitle': 'Set password in the password field below.',
        'show_password': True
    })


@staff_required
def user_edit(request, pk):
    obj = get_object_or_404(User, pk=pk)
    Form = modelform_factory(
        User,
        fields=[
            'first_name', 'last_name', 'username', 'email',
            'phone_number', 'role', 'is_active',
            'is_staff', 'is_admin', 'is_superadmin'
        ]
    )

    if request.method == 'POST':
        form = Form(request.POST, instance=obj)
        if form.is_valid():
            user = form.save()
            pwd = request.POST.get('password')
            if pwd:
                user.set_password(pwd)
                user.save()
            messages.success(request, 'User updated successfully.')
            return redirect('dashboard:user_list')
    else:
        form = Form(instance=obj)

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Edit User',
        'show_password': True
    })


@staff_required
def user_delete(request, pk):
    obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('dashboard:user_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': obj,
        'title': 'Delete User'
    })


# ---------------- DOCTORS ----------------

@staff_required
def doctor_list(request):
    q = request.GET.get('q', '').strip()

    qs = Doctor.objects.select_related('user', 'department').all().order_by('-created_at')
    if q:
        qs = qs.filter(
            Q(user__email__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(clinic_name__icontains=q) |
            Q(clinic_address__icontains=q) |
            Q(department__name__icontains=q)
        )

    page = _paginate(request, qs, 12)
    return render(request, 'dashboard/doctor_list.html', {'page': page, 'q': q})


@staff_required
def doctor_edit(request, pk):
    obj = get_object_or_404(Doctor, pk=pk)
    Form = modelform_factory(
        Doctor,
        fields=[
            'doctor_license', 'is_approved', 'biography',
            'clinic_name', 'clinic_address', 'department',
            'clinic_latitude', 'clinic_longitude',
            'contact_phone', 'contact_email'
        ]
    )

    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Doctor updated successfully.')
            return redirect('dashboard:doctor_list')
    else:
        form = Form(instance=obj)

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Edit Doctor'
    })


@staff_required
def doctor_delete(request, pk):
    obj = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Doctor deleted successfully.')
        return redirect('dashboard:doctor_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': obj,
        'title': 'Delete Doctor'
    })


# ---------------- PATIENTS ----------------

@staff_required
def patient_list(request):
    q = request.GET.get('q', '').strip()

    qs = Patient.objects.select_related('user', 'user_profile').all().order_by('-id')
    if q:
        qs = qs.filter(
            Q(user__email__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__phone_number__icontains=q) |
            Q(user_profile__city__icontains=q) |
            Q(user_profile__address__icontains=q)
        )

    page = _paginate(request, qs, 12)
    return render(request, 'dashboard/patient_list.html', {'page': page, 'q': q})


@staff_required
def patient_edit(request, pk):
    obj = get_object_or_404(Patient, pk=pk)
    Form = modelform_factory(Patient, fields=['user', 'user_profile'])

    if request.method == 'POST':
        form = Form(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient updated successfully.')
            return redirect('dashboard:patient_list')
    else:
        form = Form(instance=obj)

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Edit Patient'
    })


@staff_required
def patient_delete(request, pk):
    obj = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Patient deleted successfully.')
        return redirect('dashboard:patient_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': obj,
        'title': 'Delete Patient'
    })


# ---------------- APPOINTMENTS ----------------

@staff_required
def appointment_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    appt_type = request.GET.get('type', '').strip()

    qs = Appointment.objects.select_related(
        'doctor', 'doctor__user', 'patient', 'time_slot'
    ).all().order_by('-appointment_date', '-id')

    if q:
        qs = qs.filter(
            Q(patient__email__icontains=q) |
            Q(patient__first_name__icontains=q) |
            Q(patient__last_name__icontains=q) |
            Q(doctor__user__email__icontains=q) |
            Q(doctor__user__first_name__icontains=q) |
            Q(doctor__user__last_name__icontains=q) |
            Q(message__icontains=q)
        )

    if status:
        qs = qs.filter(appointment_status=status)

    if appt_type:
        qs = qs.filter(appointment_type=appt_type)

    page = _paginate(request, qs, 15)
    return render(request, 'dashboard/appointment_list.html', {
        'page': page,
        'q': q,
        'status': status,
        'type': appt_type,
    })


@staff_required
def appointment_edit(request, pk):
    obj = get_object_or_404(Appointment, pk=pk)
    Form = modelform_factory(
        Appointment,
        fields=[
            'appointment_date', 'time_slot', 'doctor', 'patient',
            'appointment_type', 'appointment_status', 'message',
            'image_upload'
        ]
    )

    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated successfully.')
            return redirect('dashboard:appointment_list')
    else:
        form = Form(instance=obj)

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Edit Appointment'
    })


@staff_required
def appointment_delete(request, pk):
    obj = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Appointment deleted successfully.')
        return redirect('dashboard:appointment_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': obj,
        'title': 'Delete Appointment'
    })


# ---------------- REMARKS ----------------

@staff_required
def remark_list(request):
    q = request.GET.get('q', '').strip()

    qs = Remark.objects.select_related(
        'appointment', 'doctor', 'doctor__user', 'appointment__patient'
    ).all().order_by('-created_at')

    if q:
        qs = qs.filter(
            Q(doctor__user__email__icontains=q) |
            Q(appointment__patient__email__icontains=q) |
            Q(diagnosis__icontains=q) |
            Q(symptoms__icontains=q) |
            Q(note__icontains=q) |
            Q(advice__icontains=q)
        )

    page = _paginate(request, qs, 15)
    return render(request, 'dashboard/remark_list.html', {'page': page, 'q': q})


@staff_required
def remark_edit(request, pk):
    obj = get_object_or_404(Remark, pk=pk)
    Form = modelform_factory(
        Remark,
        fields=[
            'appointment', 'doctor', 'diagnosis',
            'symptoms', 'note', 'advice', 'follow_up_date'
        ]
    )

    if request.method == 'POST':
        form = Form(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Remark updated successfully.')
            return redirect('dashboard:remark_list')
    else:
        form = Form(instance=obj)

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Edit Remark'
    })


@staff_required
def remark_delete(request, pk):
    obj = get_object_or_404(Remark, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Remark deleted successfully.')
        return redirect('dashboard:remark_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': obj,
        'title': 'Delete Remark'
    })


# ---------------- PRESCRIPTIONS ----------------

@staff_required
def prescription_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    qs = Prescription.objects.select_related(
        'doctor', 'doctor__user', 'patient', 'appointment'
    ).all().order_by('-created_at')

    if q:
        qs = qs.filter(
            Q(patient__email__icontains=q) |
            Q(patient__first_name__icontains=q) |
            Q(patient__last_name__icontains=q) |
            Q(doctor__user__email__icontains=q) |
            Q(doctor__user__first_name__icontains=q) |
            Q(doctor__user__last_name__icontains=q) |
            Q(notes__icontains=q)
        )

    if status:
        qs = qs.filter(status=status)

    page = _paginate(request, qs, 15)
    return render(request, 'dashboard/prescription_list.html', {
        'page': page,
        'q': q,
        'status': status,
    })


@staff_required
def prescription_detail(request, pk):
    obj = get_object_or_404(
        Prescription.objects.select_related(
            'doctor', 'doctor__user', 'patient', 'appointment'
        ).prefetch_related('items__medicine'),
        pk=pk
    )

    items = obj.items.select_related('medicine').all()
    dispense_record = getattr(obj, 'dispense_record', None)

    return render(request, 'dashboard/prescription_detail.html', {
        'prescription': obj,
        'items': items,
        'dispense_record': dispense_record,
    })


@staff_required
def prescription_delete(request, pk):
    obj = get_object_or_404(Prescription, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Prescription deleted successfully.')
        return redirect('dashboard:prescription_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': obj,
        'title': 'Delete Prescription'
    })


# ---------------- MEDICINES ----------------

@staff_required
def medicine_list(request):
    q = request.GET.get('q', '').strip()

    qs = Medicine.objects.all().order_by('name')
    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(generic_name__icontains=q) |
            Q(dosage_form__icontains=q) |
            Q(strength__icontains=q)
        )

    page = _paginate(request, qs, 15)
    return render(request, 'dashboard/medicine_list.html', {'page': page, 'q': q})


@staff_required
def medicine_create(request):
    Form = modelform_factory(
        Medicine,
        fields=[
            'name', 'generic_name', 'dosage_form', 'strength',
            'unit_price', 'stock_qty', 'is_active',
            'description', 'image', 'price'
        ]
    )

    if request.method == 'POST':
        form = Form(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine created successfully.')
            return redirect('dashboard:medicine_list')
    else:
        form = Form()

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Create Medicine'
    })


@staff_required
def medicine_edit(request, pk):
    obj = get_object_or_404(Medicine, pk=pk)
    Form = modelform_factory(
        Medicine,
        fields=[
            'name', 'generic_name', 'dosage_form', 'strength',
            'unit_price', 'stock_qty', 'is_active',
            'description', 'image', 'price'
        ]
    )

    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine updated successfully.')
            return redirect('dashboard:medicine_list')
    else:
        form = Form(instance=obj)

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Edit Medicine'
    })


@staff_required
def medicine_delete(request, pk):
    obj = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Medicine deleted successfully.')
        return redirect('dashboard:medicine_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': obj,
        'title': 'Delete Medicine'
    })


# ---------------- DEPARTMENTS ----------------

@staff_required
def department_list(request):
    q = request.GET.get('q', '').strip()

    qs = Department.objects.all().order_by('name')
    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q)
        )

    page = _paginate(request, qs, 12)
    return render(request, 'dashboard/department_list.html', {'page': page, 'q': q})


@staff_required
def department_create(request):
    Form = modelform_factory(
        Department,
        fields=['name', 'disease', 'description', 'image']
    )

    if request.method == 'POST':
        form = Form(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department created successfully.')
            return redirect('dashboard:department_list')
    else:
        form = Form()

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Create Department'
    })


@staff_required
def department_edit(request, pk):
    obj = get_object_or_404(Department, pk=pk)
    Form = modelform_factory(
        Department,
        fields=['name', 'disease', 'description', 'image']
    )

    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated successfully.')
            return redirect('dashboard:department_list')
    else:
        form = Form(instance=obj)

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Edit Department'
    })


@staff_required
def department_delete(request, pk):
    obj = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Department deleted successfully.')
        return redirect('dashboard:department_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': obj,
        'title': 'Delete Department'
    })


# ---------------- DISEASES ----------------

@staff_required
def disease_list(request):
    q = request.GET.get('q', '').strip()

    qs = Disease.objects.all().order_by('name')
    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q)
        )

    page = _paginate(request, qs, 12)
    return render(request, 'dashboard/disease_list.html', {'page': page, 'q': q})


@staff_required
def disease_create(request):
    Form = modelform_factory(
        Disease,
        fields=['name', 'description']
    )

    if request.method == 'POST':
        form = Form(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Disease created successfully.')
            return redirect('dashboard:disease_list')
    else:
        form = Form()

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Create Disease'
    })


@staff_required
def disease_edit(request, pk):
    obj = get_object_or_404(Disease, pk=pk)
    Form = modelform_factory(
        Disease,
        fields=['name', 'description']
    )

    if request.method == 'POST':
        form = Form(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Disease updated successfully.')
            return redirect('dashboard:disease_list')
    else:
        form = Form(instance=obj)

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Edit Disease'
    })


@staff_required
def disease_delete(request, pk):
    obj = get_object_or_404(Disease, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Disease deleted successfully.')
        return redirect('dashboard:disease_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': obj,
        'title': 'Delete Disease'
    })


# ---------------- PAYMENTS ----------------

@staff_required
def payment_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    qs = Payment.objects.select_related(
        'appointment', 'doctor', 'doctor__user', 'patient'
    ).all().order_by('-created_at')

    if q:
        qs = qs.filter(
            Q(patient__email__icontains=q) |
            Q(patient__first_name__icontains=q) |
            Q(patient__last_name__icontains=q) |
            Q(doctor__user__email__icontains=q) |
            Q(doctor__user__first_name__icontains=q) |
            Q(doctor__user__last_name__icontains=q) |
            Q(transaction_id__icontains=q)
        )

    if status:
        qs = qs.filter(payment_status=status)

    page = _paginate(request, qs, 15)
    return render(request, 'dashboard/payment_list.html', {
        'page': page,
        'q': q,
        'status': status,
    })


@staff_required
def payment_edit(request, pk):
    obj = get_object_or_404(Payment, pk=pk)
    Form = modelform_factory(
        Payment,
        fields=[
            'payment_method', 'payment_status', 'doctor_fee',
            'mediconnect_percentage', 'transaction_id', 'payment_date'
        ]
    )

    if request.method == 'POST':
        form = Form(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment updated successfully.')
            return redirect('dashboard:payment_list')
    else:
        form = Form(instance=obj)

    return render(request, 'dashboard/form.html', {
        'form': form,
        'title': 'Edit Payment'
    })


@staff_required
def payment_delete(request, pk):
    obj = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Payment deleted successfully.')
        return redirect('dashboard:payment_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': obj,
        'title': 'Delete Payment'
    })
