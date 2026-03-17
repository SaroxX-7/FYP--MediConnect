from django.shortcuts import render

from appointment.models import Appointment
from doctor.models import Doctor


# Create your views here.
def appointments(request):
    doctor = Doctor.objects.get(user=request.user)
    appointments = Appointment.objects.filter(doctor=doctor).filter(appointment_status='pending').order_by('date')
    context = {'doctor': doctor, 'appointments': appointments}
    print(f"CUSTOMERSSSS {Appointment}")
    return render(request, 'appointments.html', context)
