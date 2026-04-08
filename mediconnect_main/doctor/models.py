from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from accounts.models import User, Department


class Doctor(models.Model):
    user = models.OneToOneField(
        User,
        related_name='user',
        on_delete=models.CASCADE
    )
    doctor_license = models.ImageField(
        upload_to='doctor/license',
        blank=True,
        null=True
    )
    doctor_slug = models.SlugField(
        max_length=50,
        unique=True,
        null=True
    )
    is_approved = models.BooleanField(default=False)
    biography = models.TextField(blank=True, null=True)
    clinic_name = models.CharField(max_length=100, blank=True, null=True)
    clinic_address = models.CharField(max_length=255, blank=True, null=True)
    department = models.ForeignKey(
        Department,
        related_name='doctors',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    clinic_latitude = models.CharField(max_length=20, blank=True, null=True)
    clinic_longitude = models.CharField(max_length=20, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.doctor_slug:
            base_slug = slugify(f"{self.user.first_name}{self.user.last_name}")
            self.doctor_slug = base_slug
            num = 1

            while Doctor.objects.filter(doctor_slug=self.doctor_slug).exists():
                self.doctor_slug = f"{base_slug}-{num}"
                num += 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.email


class Specialization(models.Model):
    doctor = models.ManyToManyField(Doctor, related_name='specializations')
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Service(models.Model):
    doctor = models.ManyToManyField(Doctor, related_name='services')
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Education(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        related_name='education',
        on_delete=models.CASCADE
    )
    degree = models.CharField(max_length=100)
    institution = models.CharField(max_length=100)
    graduation_year = models.IntegerField()

    def __str__(self):
        return f"{self.degree} - {self.institution}"


class Experience(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        related_name='experience',
        on_delete=models.CASCADE
    )
    hospital_name = models.CharField(max_length=100)
    from_date = models.DateField()
    to_date = models.DateField(blank=True, null=True)
    designation = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.designation} - {self.hospital_name}"


class Award(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        related_name='awards',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    year = models.IntegerField()

    def __str__(self):
        return self.name


class Membership(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        related_name='memberships',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Registration(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        related_name='registrations',
        on_delete=models.CASCADE
    )
    registration_number = models.CharField(max_length=100)
    year = models.IntegerField()

    def __str__(self):
        return self.registration_number


class DoctorBilling(models.Model):
    doctor = models.OneToOneField(
        Doctor,
        on_delete=models.CASCADE,
        related_name='billing'
    )
    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    esewa_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    esewa_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Billing - {self.doctor.user.email}"


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
    ('cash', 'Cash'),
    ('esewa', 'eSewa'),
]


    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    appointment = models.OneToOneField(
        'appointment.Appointment',
        on_delete=models.CASCADE,
        related_name='payment'
    )
    doctor = models.ForeignKey(
        'doctor.Doctor',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )

    doctor_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    mediconnect_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00
    )
    mediconnect_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    transaction_uuid = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )
    transaction_id = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )
    payment_date = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        doctor_fee = Decimal(self.doctor_fee or 0)
        percentage = Decimal(self.mediconnect_percentage or 10)

        self.mediconnect_fee = (
            (doctor_fee * percentage) / Decimal('100')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.total_amount = (
            doctor_fee + self.mediconnect_fee
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment #{self.id} - Appointment {self.appointment.id}"