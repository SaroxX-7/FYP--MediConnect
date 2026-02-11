from django.db import models
from django.utils.text import slugify

from accounts.models import User, UserProfile, Department
from customers.models import Patient


# class Doctor(models.Model):
#     user = models.OneToOneField(User, related_name='user', on_delete=models.CASCADE)
#     user_profile = models.OneToOneField(UserProfile, related_name='userprofile', on_delete=models.CASCADE)
#     doctor_name = models.CharField(max_length=50)
#     doctor_license = models.ImageField(upload_to='doctor/license')
#     is_approved = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateTimeField(auto_now=True)
#
#     def __str__(self):
#         return self.doctor_name

class Doctor(models.Model):
    user = models.OneToOneField(User, related_name='user', on_delete=models.CASCADE)
    # user_profile = models.OneToOneField(UserProfile, related_name='userprofile', on_delete=models.CASCADE)
    doctor_license = models.ImageField(upload_to='doctor/license', blank=True, null=True)
    doctor_slug = models.SlugField(max_length=50, unique=True, null=True)
    is_approved = models.BooleanField(default=False)
    biography = models.TextField(blank=True, null=True)
    clinic_name = models.CharField(max_length=100, blank=True, null=True)
    clinic_address = models.CharField(max_length=255, blank=True, null=True)
    department = models.ForeignKey(Department, related_name='doctors', on_delete=models.CASCADE, blank=True, null=True)
    clinic_latitude = models.CharField(max_length=20, blank=True, null=True)
    clinic_longitude = models.CharField(max_length=20, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    #doctor_slug function by using the name of the doctor and add number to it if the name is already exist
    def save(self, *args, **kwargs):
        if not self.doctor_slug:
            self.doctor_slug = slugify(self.user.first_name + self.user.last_name)
            original_slug = self.doctor_slug
            num = 1
            while Doctor.objects.filter(doctor_slug=self.doctor_slug).exists():
                self.doctor_slug = f'{original_slug}-{num}'
                num += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.email

class Specialization(models.Model):
    doctor = models.ManyToManyField(Doctor, related_name='specializations')
    name = models.CharField(max_length=100)

class Service(models.Model):
    doctor = models.ManyToManyField(Doctor, related_name='services')
    name = models.CharField(max_length=100)

class Education(models.Model):
    doctor = models.ForeignKey(Doctor, related_name='education', on_delete=models.CASCADE)
    degree = models.CharField(max_length=100)
    institution = models.CharField(max_length=100)
    graduation_year = models.IntegerField()

class Experience(models.Model):
    doctor = models.ForeignKey(Doctor, related_name='experience', on_delete=models.CASCADE)
    hospital_name = models.CharField(max_length=100)
    from_date = models.DateField()
    to_date = models.DateField(blank=True, null=True)  # null for current positions
    designation = models.CharField(max_length=100)

class Award(models.Model):
    doctor = models.ForeignKey(Doctor, related_name='awards', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    year = models.IntegerField()

class Membership(models.Model):
    doctor = models.ForeignKey(Doctor, related_name='memberships', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

class Registration(models.Model):
    doctor = models.ForeignKey(Doctor, related_name='registrations', on_delete=models.CASCADE)
    registration_number = models.CharField(max_length=100)
    year = models.IntegerField()

