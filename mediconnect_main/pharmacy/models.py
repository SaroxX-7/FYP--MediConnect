from django.db import models
from django.conf import settings

from appointment.models import Appointment
from doctor.models import Doctor


class Medicine(models.Model):
    name = models.CharField(max_length=120)
    generic_name = models.CharField(max_length=120, blank=True, null=True)
    dosage_form = models.CharField(max_length=60, blank=True, null=True)  # tablet/syrup/ointment
    strength = models.CharField(max_length=60, blank=True, null=True)     # 500mg/5ml etc
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_qty = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='medicines/', blank=True, null=True, default='medicines/default.png')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} {self.strength or ''}".strip()


class Prescription(models.Model):
    STATUS = (
        ('draft', 'Draft'),
        ('sent', 'Sent to Pharmacy'),
        ('dispensed', 'Dispensed'),
    )

    appointment = models.OneToOneField(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Rx #{self.id} - {self.patient}"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, related_name='items', on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    dosage = models.CharField(max_length=100, blank=True, null=True)        # 1 tab
    frequency = models.CharField(max_length=100, blank=True, null=True)     # 2x/day
    duration_days = models.PositiveIntegerField(default=0)
    quantity = models.PositiveIntegerField(default=1)
    instructions = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.medicine} x{self.quantity}"


class DispenseRecord(models.Model):
    prescription = models.OneToOneField(Prescription, related_name='dispense_record', on_delete=models.CASCADE)
    pharmacist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    dispensed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Dispensed Rx #{self.prescription_id}"
