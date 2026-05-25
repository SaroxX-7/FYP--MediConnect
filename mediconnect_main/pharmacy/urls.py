from django.urls import path
from . import views

urlpatterns = [
    # Pharmacist
    path('pharmacist/', views.pharmacist_dashboard, name='pharmacist_dashboard'),
    path('pharmacist/profile/', views.pharmacist_profile, name='pharmacistProfile'),

    path('pharmacist/medicine/add/', views.medicine_create, name='medicine_create'),
    path('pharmacist/medicine/<int:pk>/edit/', views.medicine_edit, name='medicine_edit'),
    path('pharmacist/prescription/<int:pk>/', views.prescription_detail, name='pharmacy_prescription_detail'),
    path('pharmacist/prescription/<int:pk>/dispense/', views.dispense_prescription, name='dispense_prescription'),

    path('cart/checkout/esewa/', views.cart_checkout_esewa, name='cart_checkout_esewa'),
    path('cart/checkout/success/', views.cart_checkout_success, name='cart_checkout_success'),
    path('cart/checkout/failure/', views.cart_checkout_failure, name='cart_checkout_failure'),

    # Doctor
    path(
        'doctor/appointment/<int:appointment_id>/prescription/',
        views.doctor_prescription_for_appointment,
        name='doctor_prescription_for_appointment'
    ),

    # Patient
    path('patient/prescriptions/', views.patient_prescriptions, name='patient_prescriptions'),
    path('store/', views.pharmacy_store, name='pharmacy_store'),
    path('cart/', views.view_cart, name='view_cart'),
    path('add-to-cart/<int:medicine_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:medicine_id>/', views.remove_from_cart, name='remove_from_cart'),

    path(
        'cart/add-remark-medicines/<int:remark_id>/',
        views.add_remark_medicines_to_cart,
        name='add_remark_medicines_to_cart'
    ),
]