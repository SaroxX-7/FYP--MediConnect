from django.db import models

from accounts.models import User, UserProfile
from doctor.models import Doctor
from django.conf import settings


# Create your models here.
class Appointment(models.Model):
    APPOINTMENT_TYPE = (
        ('followup', 'followup'),
        ('checkup', 'checkup'),
    )
    APPOINTMENT_STATUS = (
        ('pending', 'pending'),
        ('confirmed', 'confirmed'),
        ('cancelled', 'cancelled'),
    )
    appointment_date = models.DateField(blank=True, null=True)
    time_slot = models.ForeignKey('TimeSlot', on_delete=models.CASCADE, blank=True, null=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    appointment_type = models.CharField(max_length=200, choices=APPOINTMENT_TYPE)
    appointment_status = models.CharField(max_length=200, choices=APPOINTMENT_STATUS)
    message = models.CharField(max_length=255, null=True, blank=True)
    image_upload = models.ImageField(upload_to='appointment/', null=True, blank=True)

    def __str__(self):
        return str(self.patient.username)
        return f"{self.patient.first_name} {self.patient.last_name} - {self.doctor.doctor_name} on {self.appointment_time}"

class TimeSlot(models.Model):
    DAY_CHOICES = [
        ('Sunday', 'Sunday'),
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
    ]
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, null=True, blank=True)
    day = models.CharField(max_length=9, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    availability = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.day}: {self.start_time} - {self.end_time}"


class Booking(models.Model):
    time_slot = models.ForeignKey('TimeSlot', on_delete=models.CASCADE, related_name='bookings')
    date = models.DateField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.time_slot} on {self.date} by {self.user}"
