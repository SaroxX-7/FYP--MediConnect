from django.contrib import admin
from .models import Appointment, TimeSlot, Booking

admin.site.register(Appointment)
admin.site.register(TimeSlot)
admin.site.register(Booking)
