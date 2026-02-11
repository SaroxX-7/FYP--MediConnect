from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import login as auth_login
from django.forms import modelform_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator

from accounts.models import User, UserProfile, Department, Disease
from doctor.models import Doctor
from appointment.models import TimeSlot, Booking
from .utils import staff_required


def _paginate(request, qs, per_page=10):
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def dashboard_login(request):
    if request.user.is_authenticated and (getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_admin', False) or getattr(request.user, 'is_superadmin', False)):
        return redirect('dashboard:home')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, email=email, password=password)
        if user is None:
            messages.error(request, 'Invalid credentials.')
            return redirect('dashboard:login')

        if not (getattr(user, 'is_staff', False) or getattr(user, 'is_admin', False) or getattr(user, 'is_superadmin', False)):
            messages.error(request, 'You are not allowed to access the dashboard.')
            return redirect('dashboard:login')

        auth_login(request, user)
        messages.success(request, 'Welcome to the dashboard.')
        return redirect('dashboard:home')

    return render(request, 'dashboard/login.html')


@staff_required
def dashboard_logout(request):
    auth_logout(request)
    messages.success(request, 'Logged out.')
    return redirect('dashboard:login')


@staff_required
def dashboard_home(request):
    context = {
        'user_count': User.objects.count(),
        'doctor_count': Doctor.objects.count(),
        'patient_count': User.objects.filter(role=User.CUSTOMER).count(),
        'timeslot_count': TimeSlot.objects.count(),
        'booking_count': Booking.objects.count(),
        'department_count': Department.objects.count(),
        'disease_count': Disease.objects.count(),
    }
    return render(request, 'dashboard/home.html', context)

# ---------------- USERS ----------------

@staff_required
def user_list(request):
    q = request.GET.get('q', '').strip()
    qs = User.objects.all().order_by('-created_date')
    if q:
        qs = qs.filter(email__icontains=q) | qs.filter(username__icontains=q) | qs.filter(first_name__icontains=q) | qs.filter(last_name__icontains=q)
    page = _paginate(request, qs, 12)
    return render(request, 'dashboard/user_list.html', {'page': page, 'q': q})


@staff_required
def user_create(request):
    Form = modelform_factory(User, fields=['first_name','last_name','username','email','phone_number','role','is_active','is_staff','is_admin','is_superadmin'])
    if request.method == 'POST':
        form = Form(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # set a default password if not provided elsewhere
            pwd = request.POST.get('password') or 'ChangeMe123!'
            user.set_password(pwd)
            user.save()
            messages.success(request, 'User created.')
            return redirect('dashboard:user_list')
    else:
        form = Form()
    return render(request, 'dashboard/form.html', {'form': form, 'title': 'Create User', 'subtitle': 'Set password in the Password field below.', 'show_password': True})


@staff_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    Form = modelform_factory(User, fields=['first_name','last_name','username','email','phone_number','role','is_active','is_staff','is_admin','is_superadmin'])
    if request.method == 'POST':
        form = Form(request.POST, instance=user)
        if form.is_valid():
            obj = form.save()
            pwd = request.POST.get('password')
            if pwd:
                obj.set_password(pwd)
                obj.save()
            messages.success(request, 'User updated.')
            return redirect('dashboard:user_list')
    else:
        form = Form(instance=user)
    return render(request, 'dashboard/form.html', {'form': form, 'title': 'Edit User', 'show_password': True})


@staff_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted.')
        return redirect('dashboard:user_list')
    return render(request, 'dashboard/confirm_delete.html', {'object': user, 'title': 'Delete User'})

# ---------------- PROFILES ----------------

@staff_required
def profile_list(request):
    q = request.GET.get('q', '').strip()
    qs = UserProfile.objects.select_related('user').all().order_by('-created_at')
    if q:
        qs = qs.filter(user__email__icontains=q) | qs.filter(user__username__icontains=q) | qs.filter(city__icontains=q)
    page = _paginate(request, qs, 12)
    return render(request, 'dashboard/profile_list.html', {'page': page, 'q': q})


@staff_required
def profile_edit(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    Form = modelform_factory(UserProfile, exclude=['location','created_at','modified_at'])
    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('dashboard:profile_list')
    else:
        form = Form(instance=profile)
    return render(request, 'dashboard/form.html', {'form': form, 'title': 'Edit User Profile'})

# ---------------- DEPARTMENTS ----------------

@staff_required
def department_list(request):
    q = request.GET.get('q', '').strip()
    qs = Department.objects.all().order_by('name')
    if q:
        qs = qs.filter(name__icontains=q)
    page = _paginate(request, qs, 12)
    return render(request, 'dashboard/department_list.html', {'page': page, 'q': q})


@staff_required
def department_create(request):
    Form = modelform_factory(Department, fields=['name','disease','description','image'])
    if request.method == 'POST':
        form = Form(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department created.')
            return redirect('dashboard:department_list')
    else:
        form = Form()
    return render(request, 'dashboard/form.html', {'form': form, 'title': 'Create Department'})


@staff_required
def department_edit(request, pk):
    obj = get_object_or_404(Department, pk=pk)
    Form = modelform_factory(Department, fields=['name','disease','description','image'])
    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated.')
            return redirect('dashboard:department_list')
    else:
        form = Form(instance=obj)
    return render(request, 'dashboard/form.html', {'form': form, 'title': 'Edit Department'})


@staff_required
def department_delete(request, pk):
    obj = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Department deleted.')
        return redirect('dashboard:department_list')
    return render(request, 'dashboard/confirm_delete.html', {'object': obj, 'title': 'Delete Department'})

# ---------------- DISEASES ----------------

@staff_required
def disease_list(request):
    q = request.GET.get('q', '').strip()
    qs = Disease.objects.all().order_by('name')
    if q:
        qs = qs.filter(name__icontains=q)
    page = _paginate(request, qs, 12)
    return render(request, 'dashboard/disease_list.html', {'page': page, 'q': q})


@staff_required
def disease_create(request):
    Form = modelform_factory(Disease, fields=['name','description'])
    if request.method == 'POST':
        form = Form(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Disease created.')
            return redirect('dashboard:disease_list')
    else:
        form = Form()
    return render(request, 'dashboard/form.html', {'form': form, 'title': 'Create Disease'})


@staff_required
def disease_edit(request, pk):
    obj = get_object_or_404(Disease, pk=pk)
    Form = modelform_factory(Disease, fields=['name','description'])
    if request.method == 'POST':
        form = Form(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Disease updated.')
            return redirect('dashboard:disease_list')
    else:
        form = Form(instance=obj)
    return render(request, 'dashboard/form.html', {'form': form, 'title': 'Edit Disease'})


@staff_required
def disease_delete(request, pk):
    obj = get_object_or_404(Disease, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Disease deleted.')
        return redirect('dashboard:disease_list')
    return render(request, 'dashboard/confirm_delete.html', {'object': obj, 'title': 'Delete Disease'})

# ---------------- DOCTORS ----------------

@staff_required
def doctor_list(request):
    q = request.GET.get('q', '').strip()
    qs = Doctor.objects.select_related('user').all().order_by('-created_at')
    if q:
        qs = qs.filter(user__email__icontains=q) | qs.filter(clinic_name__icontains=q) | qs.filter(clinic_address__icontains=q)
    page = _paginate(request, qs, 12)
    return render(request, 'dashboard/doctor_list.html', {'page': page, 'q': q})


@staff_required
def doctor_edit(request, pk):
    obj = get_object_or_404(Doctor, pk=pk)
    Form = modelform_factory(Doctor, fields=['doctor_license','is_approved','biography','clinic_name','clinic_address','department','clinic_latitude','clinic_longitude','contact_phone','contact_email'])
    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Doctor updated.')
            return redirect('dashboard:doctor_list')
    else:
        form = Form(instance=obj)
    return render(request, 'dashboard/form.html', {'form': form, 'title': 'Edit Doctor'})

# ---------------- TIMESLOTS ----------------

@staff_required
def timeslot_list(request):
    q = request.GET.get('q', '').strip()
    qs = TimeSlot.objects.select_related('doctor','doctor__user').all().order_by('doctor__user__first_name','day','start_time')
    if q:
        qs = qs.filter(doctor__user__email__icontains=q) | qs.filter(day__icontains=q)
    page = _paginate(request, qs, 15)
    return render(request, 'dashboard/timeslot_list.html', {'page': page, 'q': q})


@staff_required
def timeslot_create(request):
    Form = modelform_factory(TimeSlot, fields=['doctor','day','start_time','end_time','availability'])
    if request.method == 'POST':
        form = Form(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Time slot created.')
            return redirect('dashboard:timeslot_list')
    else:
        form = Form()
    return render(request, 'dashboard/form.html', {'form': form, 'title': 'Create Time Slot'})


@staff_required
def timeslot_edit(request, pk):
    obj = get_object_or_404(TimeSlot, pk=pk)
    Form = modelform_factory(TimeSlot, fields=['doctor','day','start_time','end_time','availability'])
    if request.method == 'POST':
        form = Form(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Time slot updated.')
            return redirect('dashboard:timeslot_list')
    else:
        form = Form(instance=obj)
    return render(request, 'dashboard/form.html', {'form': form, 'title': 'Edit Time Slot'})


@staff_required
def timeslot_delete(request, pk):
    obj = get_object_or_404(TimeSlot, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Time slot deleted.')
        return redirect('dashboard:timeslot_list')
    return render(request, 'dashboard/confirm_delete.html', {'object': obj, 'title': 'Delete Time Slot'})

# ---------------- BOOKINGS ----------------

@staff_required
def booking_list(request):
    q = request.GET.get('q', '').strip()
    qs = Booking.objects.select_related('time_slot','user','time_slot__doctor','time_slot__doctor__user').all().order_by('-created_at')
    if q:
        qs = qs.filter(user__email__icontains=q) | qs.filter(time_slot__doctor__user__email__icontains=q)
    page = _paginate(request, qs, 15)
    return render(request, 'dashboard/booking_list.html', {'page': page, 'q': q})


@staff_required
def booking_delete(request, pk):
    obj = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Booking deleted.')
        return redirect('dashboard:booking_list')
    return render(request, 'dashboard/confirm_delete.html', {'object': obj, 'title': 'Delete Booking'})
