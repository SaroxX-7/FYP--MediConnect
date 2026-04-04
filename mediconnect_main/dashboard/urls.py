from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('login/', views.dashboard_login, name='login'),
    path('logout/', views.dashboard_logout, name='logout'),
    path('', views.dashboard_home, name='home'),

    # Users
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    # Doctors
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('doctors/<int:pk>/edit/', views.doctor_edit, name='doctor_edit'),
    path('doctors/<int:pk>/delete/', views.doctor_delete, name='doctor_delete'),

    # Patients
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/<int:pk>/edit/', views.patient_edit, name='patient_edit'),
    path('patients/<int:pk>/delete/', views.patient_delete, name='patient_delete'),

    # Appointments
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/<int:pk>/edit/', views.appointment_edit, name='appointment_edit'),
    path('appointments/<int:pk>/delete/', views.appointment_delete, name='appointment_delete'),

    # Remarks
    path('remarks/', views.remark_list, name='remark_list'),
    path('remarks/<int:pk>/edit/', views.remark_edit, name='remark_edit'),
    path('remarks/<int:pk>/delete/', views.remark_delete, name='remark_delete'),

    # Prescriptions
    path('prescriptions/', views.prescription_list, name='prescription_list'),
    path('prescriptions/<int:pk>/view/', views.prescription_detail, name='prescription_detail'),
    path('prescriptions/<int:pk>/delete/', views.prescription_delete, name='prescription_delete'),

    # Medicines
    path('medicines/', views.medicine_list, name='medicine_list'),
    path('medicines/create/', views.medicine_create, name='medicine_create'),
    path('medicines/<int:pk>/edit/', views.medicine_edit, name='medicine_edit'),
    path('medicines/<int:pk>/delete/', views.medicine_delete, name='medicine_delete'),

    # Departments
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_edit, name='department_edit'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),

    # Diseases
    path('diseases/', views.disease_list, name='disease_list'),
    path('diseases/create/', views.disease_create, name='disease_create'),
    path('diseases/<int:pk>/edit/', views.disease_edit, name='disease_edit'),
    path('diseases/<int:pk>/delete/', views.disease_delete, name='disease_delete'),

    # Payments
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/<int:pk>/edit/', views.payment_edit, name='payment_edit'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
]