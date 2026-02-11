from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('login/', views.dashboard_login, name='login'),
    path('logout/', views.dashboard_logout, name='logout'),
    path('', views.dashboard_home, name='home'),

    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    path('profiles/', views.profile_list, name='profile_list'),
    path('profiles/<int:pk>/edit/', views.profile_edit, name='profile_edit'),

    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_edit, name='department_edit'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),

    path('diseases/', views.disease_list, name='disease_list'),
    path('diseases/create/', views.disease_create, name='disease_create'),
    path('diseases/<int:pk>/edit/', views.disease_edit, name='disease_edit'),
    path('diseases/<int:pk>/delete/', views.disease_delete, name='disease_delete'),

    path('doctors/', views.doctor_list, name='doctor_list'),
    path('doctors/<int:pk>/edit/', views.doctor_edit, name='doctor_edit'),

    path('timeslots/', views.timeslot_list, name='timeslot_list'),
    path('timeslots/create/', views.timeslot_create, name='timeslot_create'),
    path('timeslots/<int:pk>/edit/', views.timeslot_edit, name='timeslot_edit'),
    path('timeslots/<int:pk>/delete/', views.timeslot_delete, name='timeslot_delete'),

    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/<int:pk>/delete/', views.booking_delete, name='booking_delete'),
]
