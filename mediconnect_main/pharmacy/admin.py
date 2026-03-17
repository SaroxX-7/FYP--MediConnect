from django.contrib import admin

from .models import Medicine, Prescription, PrescriptionItem, DispenseRecord


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'dosage_form', 'strength', 'unit_price', 'stock_qty', 'is_active')
    search_fields = ('name', 'generic_name')
    list_filter = ('is_active', 'dosage_form')


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('patient__email', 'patient__username', 'doctor__user__email')
    inlines = [PrescriptionItemInline]


@admin.register(DispenseRecord)
class DispenseRecordAdmin(admin.ModelAdmin):
    list_display = ('prescription', 'pharmacist', 'dispensed_at')
