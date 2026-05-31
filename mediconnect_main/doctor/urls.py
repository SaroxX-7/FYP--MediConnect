from django.urls import path
from accounts import views as AccountViews
from . import views

urlpatterns = [
    path('', AccountViews.doctorDashboard, name='doctor'),
    path('profile/', views.dprofile, name='dprofile'),
    path('add_time_slot/', views.add_time_slot, name='add_time_slot'),
    path('time_slot/delete/<int:slot_id>/', views.delete_time_slot, name='delete_time_slot'),
    path('time_slots/', views.time_slots, name='time_slots'),
    path('doc_appointments/', views.appointments, name='doctorAppointments'),

    path(
        'appointment/<int:appointment_id>/doctor-details/',
        views.doctor_appointment_details,
        name='doctor_appointment_details'
    ),
    path(
        'appointment/<int:appointment_id>/',
        views.appointment_details,
        name='appointment_details'
    ),
    path(
        'appointment/<int:appointment_id>/complete/',
        views.complete_appointment,
        name='complete_appointment'
    ),
    path(
        'appointment/<int:appointment_id>/create-followup/',
        views.create_followup_appointment,
        name='create_followup_appointment'
    ),

    path('appointment/accept/<int:appointment_id>/', views.accept_appointment, name='accept_appointment'),
    path('appointment/reject/<int:appointment_id>/', views.reject_appointment, name='reject_appointment'),
    path('download-prescription/<int:appointment_id>/', views.download_prescription_pdf, name='download_prescription_pdf'),

    path('<slug:doctor_slug>/', views.doctor_detail, name='doctor_detail'),
]
