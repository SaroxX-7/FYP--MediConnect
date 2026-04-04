from django.shortcuts import render
from appointment.models import Appointment
from doctor.models import Doctor


def appointments(request):
    doctor = Doctor.objects.get(user=request.user)
    appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_status='pending'
    ).order_by('appointment_date', 'time_slot__start_time')

    context = {
        'doctor': doctor,
        'appointments': appointments
    }
    return render(request, 'appointments.html', context)