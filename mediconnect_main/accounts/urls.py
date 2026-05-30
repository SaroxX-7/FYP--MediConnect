from django.urls import path, include
from . import views


urlpatterns = [
    path('registerUser/', views.registerUser, name='registerUser'),
    path('registerDoctor/', views.registerDoctor, name='registerDoctor'),
    path('registerPharmacist/', views.registerPharmacist, name='registerPharmacist'),

    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('myAccount/', views.myAccount, name='myAccount'),
    path('custDashboard/', views.custDashboard, name='custDashboard'),
    path('doctorDashboard/', views.doctorDashboard, name='doctorDashboard'),
    path('pharmacistDashboard/', views.pharmacistDashboard, name='pharmacistDashboard'),

    path('activate/<uidb64>/<token>/', views.activate, name='activate'),

    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('reset_password_validate/<uidb64>/<token>/', views.reset_password_validate, name='reset_password_validate'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('change_password/', views.change_password, name='change_password'),
    # path('customer/', include('customers.urls')),
    # path('doctor/', include('doctor.urls')),
    path('settings/security/update-password/', views.change_password_view, name='update_password'),
    path('verify-email/<uidb64>/', views.verify_email_code, name='verify_email_code'),
    path('resend-verification-code/<uidb64>/', views.resend_verification_code, name='resend_verification_code'),
    path('verify-forgot-password-code/<uidb64>/', views.verify_forgot_password_code, name='verify_forgot_password_code'),
]