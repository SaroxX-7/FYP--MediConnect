from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/', include('accounts.urls')),
    path('panel/', include('dashboard.urls')),
    path('doctor/', include('doctor.urls')),
    path('customer/', include('customers.urls')),
    path('pharmacy/', include('pharmacy.urls')),
    path('chat/', include('chat.urls')),
    path('payments/', include('payments.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
