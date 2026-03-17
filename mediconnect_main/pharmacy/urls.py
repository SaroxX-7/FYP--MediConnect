from django.urls import path

from . import views

urlpatterns = [
    # Pharmacist
    path('pharmacist/', views.pharmacist_dashboard, name='pharmacist_dashboard'),
    path('pharmacist/medicine/add/', views.medicine_create, name='medicine_create'),
    path('pharmacist/medicine/<int:pk>/edit/', views.medicine_edit, name='medicine_edit'),
    path('pharmacist/prescription/<int:pk>/', views.prescription_detail, name='pharmacy_prescription_detail'),
    path('pharmacist/prescription/<int:pk>/dispense/', views.dispense_prescription, name='dispense_prescription'),

    # Doctor
    path('doctor/appointment/<int:appointment_id>/prescription/', views.doctor_prescription_for_appointment, name='doctor_prescription_for_appointment'),

    # Patient
    path('patient/prescriptions/', views.patient_prescriptions, name='patient_prescriptions'),
]
