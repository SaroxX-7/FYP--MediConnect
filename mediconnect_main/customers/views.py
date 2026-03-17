from datetime import datetime, timedelta

from django.http import HttpResponse
from django.utils.dateparse import parse_date
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from accounts.forms import UserInfoForm, UserProfileForm
from accounts.models import UserProfile, User, Department, Disease
from django.contrib import messages

from appointment.forms import AppointmentForm
from appointment.models import TimeSlot, Appointment, Booking
from doctor.models import Doctor
from django.db.models import Prefetch

from django.db.models import Q
from django.contrib.gis.geos import Point
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import D # ``D`` is a shortcut for ``Distance``
from django.contrib.gis.db.models.functions import Distance
from appointment.models import Appointment, Remark, RemarkMedicine



@login_required(login_url='login')
def cprofile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        image = request.FILES.get('profile_picture')
        print("image is", image)

        user_form = UserInfoForm(request.POST, instance=request.user)
        if profile_form.is_valid() and user_form.is_valid():
            print (profile_form)
            profile_form.save()
            user_form.save()
            print("doneeeee")
            messages.success(request, 'Profile updated')
            return redirect('cprofile')
        else:
            print(profile_form.errors)
            print(user_form.errors)
    else:
        profile_form = UserProfileForm(instance=profile)
        user_form = UserInfoForm(instance=request.user)

    # Assuming `profile_form.date_of_birth.value` is a date or datetime object
    formatted_date = profile_form.instance.date_of_birth
    dob = profile.date_of_birth
    age = None  # Default age is None if no date_of_birth provided
    if dob:
        age = (datetime.now().date() - dob).days // 365  # Calculate age

    context = {
        'profile_form': profile_form,
        'user_form' : user_form,
        'profile': profile,
        'formatted_date': formatted_date,
        'age': age,
    }
    print ("view successfully called")
    return render(request, 'customers/cprofile.html', context)


class DoctorsByDepartmentView(ListView):
    model = Doctor
    template_name = 'customers/doctors_by_department.html'

    def get_queryset(self):
        """
        Override the get_queryset method to filter doctors by the department slug.
        """
        department_slug = self.kwargs.get('department_slug')
        diseases_prefetch = Prefetch('department__disease', queryset=Disease.objects.all())
        return Doctor.objects.filter(department__slug=department_slug).select_related('user__userprofile').prefetch_related(diseases_prefetch)

    def get_context_data(self, **kwargs):
        """
        Add the department to the context.
        """
        context = super().get_context_data(**kwargs)
        department_slug = self.kwargs.get('department_slug')
        context['department'] = Department.objects.filter(slug=department_slug).first()
        return context


# def search_doctors(request):
#     query = request.GET.get('query', '')
#     doctors = Doctor.objects.all()
#
#     if query:
#         # Attempt to find a matching disease or department
#         disease = Disease.objects.filter(name__iexact=query).first()
#         department = Department.objects.filter(name__iexact=query).first()
#
#         if disease:
#             doctors = doctors.filter(department__disease=disease)
#         elif department:
#             doctors = doctors.filter(department=department)
#         else:
#             # If no disease or department matches the query, return no results
#             doctors = Doctor.objects.none()
#
#     # doctors_list = [{"name": doctor.user.get_full_name(), "department": doctor.department.name} for doctor in doctors]
#
#     return render(request, 'customers/search_doctors.html', {'query': query, 'object_list': doctors, 'query': query})

# def search_doctors(request):
#     query = request.GET.get('query', '')
#     latitude = request.GET.get('lat', '')
#     longitude = request.GET.get('lng', '')
#     radius = request.GET.get('radius', '')
#     doctors = Doctor.objects.all()
#
#     # Preparing a default far away point if no valid location is provided
#     default_location = Point(0, 0, srid=4326)
#
#     # Check if location parameters exist
#     if latitude and longitude:
#         try:
#             user_location = Point(float(longitude), float(latitude), srid=4326)
#         except ValueError:
#             user_location = default_location  # Invalid data leads to default location
#     else:
#         user_location = default_location
#
#     # Annotate all doctors with distance regardless of whether we'll use it
#     doctors = doctors.annotate(
#         distance=Distance("userprofile__location", user_location)
#     )
#
#     # Search by disease or department
#     if query:
#         disease = Disease.objects.filter(name__iexact=query).first()
#         department = Department.objects.filter(name__iexact=query).first()
#
#         if disease:
#             doctors = doctors.filter(department__disease=disease)
#         elif department:
#             doctors = doctors.filter(department=department)
#         else:
#             # General search when no disease or department matches
#             doctors = doctors.filter(Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query))
#
#     # Apply distance filtering if a valid radius is given
#     if radius:
#         try:
#             radius_km = float(radius)
#             doctors = doctors.filter(distance__lte=D(km=radius_km)).order_by("distance")
#         except ValueError:
#             # Handle case where radius is not a valid float
#             pass
#
#     doctors_list = [{
#         "doctor": doctor,
#         "department": doctor.department.name if doctor.department else "No department",
#         "distance": f"{doctor.distance.km:.2f} km" if doctor.distance else "N/A"
#     } for doctor in doctors]
#
#     return render(request, 'customers/search_doctors.html', {
#         'query': query,
#         'object_list': doctors_list,
#     })
#

# def search_doctors(request):
#     query = request.GET.get('query', '')
#     latitude = request.GET.get('lat', '')
#     longitude = request.GET.get('lng', '')
#     radius = request.GET.get('radius', '')
#
#     # First, determine if there are any specific diseases or departments being queried
#     disease = Disease.objects.filter(name__iexact=query).first()
#     department = Department.objects.filter(name__iexact=query).first()
#
#     # Collect doctor IDs based on disease or department
#     doctor_ids = []
#     if disease:
#         doctor_ids = Doctor.objects.filter(department__disease=disease).values_list('id', flat=True)
#     elif department:
#         doctor_ids = Doctor.objects.filter(department=department).values_list('id', flat=True)
#
#     # Construct the main query
#     if doctor_ids:
#         doctors = Doctor.objects.filter(id__in=doctor_ids)
#     else:
#         # General search based on the user's name if no specific disease or department
#         doctors = Doctor.objects.filter(Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query))
#
#     # Location-based filtering
#     if latitude and longitude and radius:
#         pnt = GEOSGeometry(f'POINT({longitude} {latitude})', srid=4326)
#         doctors = doctors.annotate(distance=Distance("user__userprofile__location", pnt)).filter(distance__lte=D(km=float(radius))).order_by("distance")
#
#         # Include additional details for rendering in the template if needed
#     doctors_list = [{
#         "doctor": doctor,
#         "department": doctor.department.name if doctor.department else "No department",
#         "distance": f"{doctor.distance.km:.2f}" if hasattr(doctor, 'distance') else "N/A"
#     } for doctor in doctors]
#
#
#     context = {
#         'doctors': doctors,
#         'query': query,
#         'object_list': doctors_list,
#     }
#
#     return render(request, 'customers/search_doctors.html', context)
#
from django.shortcuts import render
from django.contrib.gis.geos import GEOSGeometry, Point
from django.contrib.gis.db.models.functions import Distance
from django.db.models import Q

def search_doctors(request):
    query = request.GET.get('query', '')
    # latitude = request.GET.get('lat', '')
    # longitude = request.GET.get('lng', '')
    # radius = request.GET.get('radius', '')

    # First, determine if there are any specific diseases or departments being queried
    disease = Disease.objects.filter(name__iexact=query).first()
    department = Department.objects.filter(name__iexact=query).first()

    # Collect doctor IDs based on disease or department
    doctor_ids = []
    if disease:
        doctor_ids = Doctor.objects.filter(department__disease=disease).values_list('id', flat=True)
    elif department:
        doctor_ids = Doctor.objects.filter(department=department).values_list('id', flat=True)

    # Construct the main query
    if doctor_ids:
        doctors = Doctor.objects.filter(id__in=doctor_ids)
    else:
        # General search based on the user's name if no specific disease or department
        doctors = Doctor.objects.filter(Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query))

        # If no doctors are found from the general search, perform a similar search for like results
        if not doctors.exists():
            doctors = Doctor.objects.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(department__name__icontains=query) |
                Q(department__disease__name__icontains=query)
            ).distinct()

    # Location-based filtering
    if latitude and longitude and radius:
        pnt = GEOSGeometry(f'POINT({longitude} {latitude})', srid=4326)
        doctors = doctors.annotate(distance=Distance("user__userprofile__location", pnt)).filter(distance__lte=D(km=float(radius))).order_by("distance")

    # Include additional details for rendering in the template if needed
    doctors_list = [{
        "doctor": doctor,
        "department": doctor.department.name if doctor.department else "No department",
        "distance": f"{doctor.distance.km:.2f}" if hasattr(doctor, 'distance') else "N/A"
    } for doctor in doctors]

    context = {
        'doctors': doctors,
        'query': query,
        'object_list': doctors_list,
    }

    return render(request, 'customers/search_doctors.html', context)


# @require_http_methods(["POST"])
# def book_appointment(request):
#     time_slot_id = request.POST.get('time_slot_id')
#     doctor_id = request.POST.get('doctor_id')
#     patient_id = request.user.id  # Assuming the user is logged in
#     appointment_type = request.POST.get('appointment_type')
#     appointment_date = request.POST.get('appointment_date')
#     message = request.POST.get('message', '')
#
#
#     appointment = Appointment(
#         time_slot_id=time_slot_id,
#         doctor_id=doctor_id,
#         appointment_date=appointment_date,
#         patient_id=patient_id,
#         appointment_type=appointment_type,
#         appointment_status='pending',
#         message=message
#     )
#
#     appointment.save()
#     time_slot = TimeSlot.objects.get(id=time_slot_id)
#     time_slot.availability = False
#     time_slot.save()
#
#     #get appointment id of the appointment just created
#     appointment_id = appointment.id
#     print("appointment_id",appointment_id)
#     return redirect('appointment_details', appointment_id=appointment_id)
#

@require_http_methods(["POST"])
def book_appointment(request):
    time_slot_id = request.POST.get('time_slot_id')
    doctor_id = request.POST.get('doctor_id')
    patient_id = request.user.id  # Assuming the user is logged in
    appointment_type = request.POST.get('appointment_type')
    appointment_date_str = request.POST.get('appointment_date')
    message = request.POST.get('message', '')
    image_upload = request.FILES.get('image_upload')

    appointment_date = parse_date(appointment_date_str)
    if appointment_date is None:
        messages.error(request, "Invalid date format.")
        return HttpResponse("Invalid date format.", status=400)

    # Begin transaction to ensure both booking and appointment creation are successful
    with transaction.atomic():
        time_slot = get_object_or_404(TimeSlot, id=time_slot_id)
        # Check if the slot is already booked
        if Booking.objects.filter(time_slot=time_slot, date=appointment_date).exists():
            messages.error(request, "This time slot is already booked.")
            return HttpResponse("This slot is already booked.", status=400)

        # Create the booking
        Booking.objects.create(time_slot=time_slot, date=appointment_date, user=request.user)

        # Create the appointment
        appointment = Appointment(
            time_slot_id=time_slot_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date_str,
            patient_id=patient_id,
            appointment_type=appointment_type,
            appointment_status='pending',
            message=message,
            image_upload=image_upload
        )
        appointment.save()

        # Update the time slot availability
        time_slot.availability = False
        time_slot.save()

    messages.success(request, "Your appointment has been successfully booked!")
    # Redirect to the appointment details page
    return redirect('appointment_details', appointment_id=appointment.id)


def get_week_dates(start_date=None):
    if start_date is None:
        start_date = datetime.today()
    start_of_week = start_date - timedelta(days=start_date.weekday())
    return [start_of_week + timedelta(days=i) for i in range(7)]

# @login_required
# def available_appointment(request, doctor_id, start_date=None):
#     doctor = get_object_or_404(Doctor, id=doctor_id)
#     if start_date:
#         start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
#     else:
#         start_date = datetime.today().date()
#
#     week_dates = get_week_dates(start_date)
#     # Format the time_slots dictionary with day names as keys
#     time_slots = {}
#     for date in week_dates:
#         day_name = date.strftime("%A").lower()  # Use lowercase to match the template access
#         slots = TimeSlot.objects.filter(doctor=doctor,
#                                         day=day_name.capitalize())  # Capitalize to match your DAY_CHOICES in the model
#         time_slots[day_name] = slots
#     for date in week_dates:
#         day_name = date.strftime("%A")
#     today = datetime.today().strftime('%Y-%m-%d')
#     context = {
#         'current_date': today,
#         'doctor': doctor,
#         'time_slots': time_slots,
#         'week_dates': week_dates
#     }
#     return render(request, 'customers/booking.html', context)


@login_required
def available_appointment(request, doctor_id, start_date=None):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    now = datetime.now()
    start_date = now.date() if not start_date else datetime.strptime(start_date, "%Y-%m-%d").date()

    # Calculate the week dates starting from the given or current date
    week_dates = [start_date + timedelta(days=i) for i in range(7)]

    # Prepare a dictionary to hold time slots and their booking statuses
    time_slots = {}
    for date in week_dates:
        day_name = date.strftime("%A").lower()  # Use lowercase to match template access
        slots = TimeSlot.objects.filter(doctor=doctor, day=day_name.capitalize())
        time_slots[day_name] = []
        for slot in slots:
            slot_time = datetime.combine(date, slot.start_time)
            # Check if there is a booking for this slot on the given date
            is_booked = Booking.objects.filter(time_slot=slot, date=date).exists()
            # Check if the slot time has passed or is less than 2 hours from now
            if slot_time < now + timedelta(hours=2):
                is_booked = True  # Treat past slots or slots too soon as 'booked' for display purposes
            time_slots[day_name].append({
                'slot': slot,
                'is_booked': is_booked
            })

    context = {
        'current_date': now.strftime('%Y-%m-%d'),
        'doctor': doctor,
        'time_slots': time_slots,
        'week_dates': week_dates
    }
    return render(request, 'customers/booking.html', context)


def appointment_details(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related(
            'doctor',
            'patient',
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
        ),
        pk=appointment_id
    )

    return render(request, 'customers/appointment_details.html', {
        'appointment': appointment,
    })

def searchByLocation(request):
    if not 'address' in request.GET:
        return redirect('marketplace')
    else:
        address = request.GET['address']
        latitude = request.GET['lat']
        longitude = request.GET['lng']
        radius = request.GET['radius']
        keyword = request.GET['keyword']

        if latitude and longitude and radius:
            pnt = GEOSGeometry('POINT(%s %s)' % (longitude, latitude))

            doctors  = Doctor.objects.filter(Q(vendor_name__icontains=keyword, is_approved=True, user__is_active=True),
            user_profile__location__distance_lte=(pnt, D(km=radius))
            ).annotate(distance=Distance("user_profile__location", pnt)).order_by("distance")

            for v in doctors :
                v.kms = round(v.distance.km, 1)
        doctor_count = doctors.count()
        context = {
            'vendors': doctors,
            'vendor_count': doctor_count,
            'source_location': address,
        }


        return render(request, 'marketplace/listings.html', context)