from django.contrib import admin

# Register your models here.

from .models import Appointment, TimeSlot, Booking

admin.site.register(Appointment)
admin.site.register(TimeSlot)
admin.site.register(Booking)

