from django.urls import path
from accounts import views as AccountViews
from . import views

urlpatterns = [
    path('', AccountViews.custDashboard, name='customer'),
    path('profile/', views.cprofile, name='cprofile'),
    # path('category/<slug:general_category_slug>/', views.marketplace_by_general_category, name='marketplace_by_general_category'),
    path('departments/<slug:department_slug>/', views.DoctorsByDepartmentView.as_view(), name='doctors-by-department'),
    path('search/doctors/', views.search_doctors, name='search_doctors'),
    path('doctors/appointments/book', views.book_appointment, name='book_appointment'),
    path('doctors/<int:doctor_id>/appointments', views.available_appointment, name='available_appointment'),
    path('appointment/<int:appointment_id>/', views.appointment_details, name='appointment_details'),
]
