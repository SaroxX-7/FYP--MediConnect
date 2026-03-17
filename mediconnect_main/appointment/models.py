from django.conf import settings
from django.db import models
from accounts.models import User
from doctor.models import Doctor


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
        return f"{self.patient.username} - {self.doctor} - {self.appointment_date}"


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


class Remark(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='remarks'
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='remarks'
    )
    diagnosis = models.TextField(blank=True, null=True)
    symptoms = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    advice = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Remark for Appointment #{self.appointment.id}"


class RemarkMedicine(models.Model):
    remark = models.ForeignKey(
        Remark,
        on_delete=models.CASCADE,
        related_name='medicines'
    )
    medicine = models.ForeignKey(
        'pharmacy.Medicine',
        on_delete=models.CASCADE,
        related_name='remark_medicines'
    )

    dosage = models.CharField(max_length=100, blank=True, null=True)  
    quantity = models.PositiveIntegerField(default=1)                 
    frequency = models.CharField(max_length=100, blank=True, null=True) 
    duration = models.CharField(max_length=100, blank=True, null=True) 
    instruction = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.medicine} for Remark #{self.remark.id}"