from django import forms
from .models import Appointment, TimeSlot


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        exclude = ['doctor', 'patient', 'appointment_status']
