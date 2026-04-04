from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
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
        ('completed', 'completed'),
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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'appointment_date', 'time_slot'],
                name='unique_doctor_date_timeslot'
            ),
            models.UniqueConstraint(
                fields=['patient', 'appointment_date', 'time_slot'],
                name='unique_patient_date_timeslot'
            ),
        ]

    def clean(self):
        # Skip duplicate check when updating to confirmed status
        is_status_update = self.pk and Appointment.objects.filter(pk=self.pk).exists()
        
        if self.doctor and self.appointment_date and self.time_slot:
            doctor_conflict = Appointment.objects.filter(
                doctor=self.doctor,
                appointment_date=self.appointment_date,
                time_slot=self.time_slot
            ).exclude(pk=self.pk)

            if doctor_conflict.exists():
                raise ValidationError("This doctor already has an appointment in this time slot.")

        if self.patient and self.appointment_date and self.time_slot:
            patient_conflict = Appointment.objects.filter(
                patient=self.patient,
                appointment_date=self.appointment_date,
                time_slot=self.time_slot
            ).exclude(pk=self.pk)

            if patient_conflict.exists():
                raise ValidationError("This patient already has an appointment in this time slot.")

        # Only check for duplicate active appointments when creating NEW appointment
        # Skip this check when updating existing appointment status
        if (self.patient and self.doctor and 
            self.appointment_status in ['pending', 'confirmed'] and 
            not is_status_update):  # Only for new appointments, not status updates
            active_same_doctor = Appointment.objects.filter(
                patient=self.patient,
                doctor=self.doctor,
                appointment_status__in=['pending', 'confirmed']
            ).exclude(pk=self.pk)

            if active_same_doctor.exists():
                raise ValidationError("You already have an active appointment with this doctor.")

        # Only block follow-up creation if there is no completed previous appointment.
        # Skip this check when updating an existing follow-up record.
        if (
            self.appointment_type == 'followup'
            and self.patient
            and self.doctor
            and not self.pk
        ):
            previous_completed = Appointment.objects.filter(
                patient=self.patient,
                doctor=self.doctor,
                appointment_status='completed'
            ).exists()

            if not previous_completed:
                raise ValidationError("Follow-up appointment can only be created after a completed appointment.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        patient_name = self.patient.username if self.patient else "No Patient"
        return f"{patient_name} - {self.doctor} - {self.appointment_date}"


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['time_slot', 'date'],
                name='unique_timeslot_date_booking'
            ),
            models.UniqueConstraint(
                fields=['user', 'date', 'time_slot'],
                name='unique_user_date_timeslot_booking'
            ),
        ]

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