from django.urls import path
from . import views

urlpatterns = [
    path('pay/<int:payment_id>/', views.initiate_payment, name='esewa_pay'),
    path('success/', views.payment_success, name='payment_success'),
    path('failure/', views.payment_failure, name='payment_failure'),
]
