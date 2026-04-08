import base64
import hashlib
import hmac
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.core.serializers import serialize


from accounts.models import UserProfile, Department, Disease


def home(request):
    user_authenticated = request.user.is_authenticated
    department = Department.objects.all().distinct()
    print(department)

    diseases = Disease.objects.all()
    diseases_json = serialize('json', diseases)
    department_json = serialize('json', department)
    if user_authenticated:
        profile = get_object_or_404(UserProfile, user=request.user)
        return render(request, 'home.html', {'profile': profile, 'department': department, 'diseases_json': diseases_json, 'department_json': department_json})
    else:
        profile = ""
        return render(request, 'home.html', {'profile': profile, 'department': department, 'diseases_json': diseases_json, 'department_json': department_json})

    return render(request, 'home.html')