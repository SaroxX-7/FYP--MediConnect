from django.contrib import admin
from doctor.models import Doctor


class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_approved', 'created_at')
    list_display_links = ('user',)

admin.site.register(Doctor, DoctorAdmin)