from datetime import timedelta
import json

from django.core.serializers import serialize
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Department
from appointment.models import TimeSlot, Booking
from doctor.models import Doctor

# If you have a Disease model, keep this import.
# If your Disease model is in another app, change the import path.
from customers.models import Disease


DAY_NAME_TO_INDEX = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def get_next_available_date_for_doctor(doctor, days_ahead=30):
    """
    Find the next available date for a doctor based on:
    - weekly TimeSlot records
    - date-wise Booking records
    """
    today = timezone.localdate()

    slots = TimeSlot.objects.filter(
        doctor=doctor,
        availability=True
    ).order_by("day", "start_time")

    if not slots.exists():
        return None

    slots_by_day = {}
    for slot in slots:
        slots_by_day.setdefault(slot.day, []).append(slot)

    for offset in range(days_ahead + 1):
        check_date = today + timedelta(days=offset)
        weekday_index = check_date.weekday()  # Monday=0 ... Sunday=6

        matching_day_name = None
        for day_name, index in DAY_NAME_TO_INDEX.items():
            if index == weekday_index:
                matching_day_name = day_name
                break

        if not matching_day_name:
            continue

        day_slots = slots_by_day.get(matching_day_name, [])

        for slot in day_slots:
            already_booked = Booking.objects.filter(
                time_slot=slot,
                date=check_date
            ).exists()

            if not already_booked:
                return check_date

    return None


def home(request):
    doctors = Doctor.objects.select_related(
        "user",
        "department",
        "user__userprofile"
    ).filter(is_approved=True)

    for doctor in doctors:
        doctor.next_available = get_next_available_date_for_doctor(doctor)

    department = Department.objects.all()
    diseases = Disease.objects.all()

    department_json = serialize("json", department)
    diseases_json = serialize("json", diseases)

    context = {
        "doctors": doctors,
        "department": department,
        "department_json": department_json,
        "diseases_json": diseases_json,
    }

    return render(request, "index.html", context)
