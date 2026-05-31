from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.conf import settings
from django.core.cache import cache
import secrets
from django.urls import reverse

def detectUser(user):
    if user.role == 1:
        redirectUrl = 'doctorDashboard'
        return redirectUrl
    elif user.role == 2:
        redirectUrl = 'custDashboard'
        return redirectUrl
    elif user.role == 3:
        redirectUrl = 'pharmacist_dashboard'
        return redirectUrl
    elif user.role == None and user.is_superadmin:
        redirectUrl = '/admin'
        return redirectUrl


def send_verification_email(request, user, mail_subject, email_template):
    from_email = settings.DEFAULT_FROM_EMAIL
    current_site = get_current_site(request)
    message = render_to_string(email_template, {
        'user': user,
        'domain': current_site,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    })
    to_email = user.email
    mail = EmailMessage(mail_subject, message, from_email, to=[to_email])
    mail.send()


def send_notification(mail_subject, mail_template, context):
    from_email = settings.DEFAULT_FROM_EMAIL
    message = render_to_string(mail_template, context)
    if (isinstance(context['to_email'], str)):
        to_email = []
        to_email.append(context['to_email'])
    else:
        to_email = context['to_email']
    mail = EmailMessage(mail_subject, message, from_email, to=to_email)
    mail.content_subtype = "html"
    mail.send()



def generate_email_verification_code():
    """
    Generates secure 6-digit code.
    Example: 482913
    """
    return str(secrets.randbelow(900000) + 100000)


def get_account_verification_cache_keys(user_id):
    """
    Two cache keys:
    1. code key
    2. attempts key
    """
    code_key = f'account_verification_code_{user_id}'
    attempts_key = f'account_verification_attempts_{user_id}'
    return code_key, attempts_key


def delete_account_verification_cache(user_id):
    """
    Delete code and attempts after successful verification
    or after too many wrong attempts.
    """
    code_key, attempts_key = get_account_verification_cache_keys(user_id)
    cache.delete(code_key)
    cache.delete(attempts_key)


def send_account_verification_code_email(request, user):
    """
    Sends 6-digit email verification code and stores code in LocMemCache.
    """
    code = generate_email_verification_code()
    timeout = getattr(settings, 'EMAIL_VERIFICATION_CODE_TIMEOUT', 600)

    code_key, attempts_key = get_account_verification_cache_keys(user.pk)

    cache.set(code_key, code, timeout)
    cache.set(attempts_key, 0, timeout)

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    verify_url = request.build_absolute_uri(
        reverse('verify_email_code', kwargs={'uidb64': uidb64})
    )

    message = render_to_string('accounts/email/account_verification_code_email.html', {
        'user': user,
        'verification_code': code,
        'verify_url': verify_url,
        'expires_minutes': timeout // 60,
    })

    mail_subject = 'Your MediConnect verification code'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = user.email

    mail = EmailMessage(mail_subject, message, from_email, to=[to_email])
    mail.content_subtype = "html"
    mail.send()

def get_password_reset_cache_keys(user_id):
    code_key = f'password_reset_code_{user_id}'
    attempts_key = f'password_reset_attempts_{user_id}'
    return code_key, attempts_key


def delete_password_reset_cache(user_id):
    code_key, attempts_key = get_password_reset_cache_keys(user_id)
    cache.delete(code_key)
    cache.delete(attempts_key)


def send_password_reset_code_email(request, user):
    """
    Sends 6-digit password reset code and stores it in LocMemCache.
    """
    code = generate_email_verification_code()
    timeout = getattr(settings, 'EMAIL_VERIFICATION_CODE_TIMEOUT', 600)

    code_key, attempts_key = get_password_reset_cache_keys(user.pk)

    cache.set(code_key, code, timeout)
    cache.set(attempts_key, 0, timeout)

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

    verify_url = request.build_absolute_uri(
        reverse('verify_forgot_password_code', kwargs={'uidb64': uidb64})
    )

    message = render_to_string('accounts/email/password_reset_code_email.html', {
        'user': user,
        'verification_code': code,
        'verify_url': verify_url,
        'expires_minutes': timeout // 60,
    })

    mail_subject = 'Your MediConnect password reset code'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = user.email

    mail = EmailMessage(mail_subject, message, from_email, to=[to_email])
    mail.content_subtype = "html"
    mail.send()
