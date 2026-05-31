from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from appointment.models import Appointment
from chat.models import Conversation, Message


def room(request):
    return render(request, "chat/room.html")


@login_required(login_url='login')
def start_chat(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related('doctor__user__userprofile', 'patient__userprofile'),
        id=appointment_id
    )

    if request.user != appointment.patient and request.user != appointment.doctor.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    conversation, created = Conversation.objects.get_or_create(
        appointment=appointment
    )

    other_user = appointment.doctor.user if request.user == appointment.patient else appointment.patient

    other_user_image = ''
    if hasattr(other_user, 'userprofile') and other_user.userprofile and other_user.userprofile.profile_picture:
        try:
            other_user_image = other_user.userprofile.profile_picture.url
        except Exception:
            other_user_image = ''

    other_user_name = f"{other_user.first_name} {other_user.last_name}"
    if request.user == appointment.patient:
        other_user_name = f"Dr. {other_user_name}"

    return JsonResponse({
        'conversation_id': conversation.id,
        'other_user_name': other_user_name,
        'other_user_image': other_user_image,
    })


@login_required(login_url='login')
def conversation_messages(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.select_related('appointment__doctor__user', 'appointment__patient'),
        id=conversation_id
    )

    if request.user != conversation.appointment.patient and request.user != conversation.appointment.doctor.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    Message.objects.filter(
        conversation=conversation,
        is_read=False
    ).exclude(
        sender=request.user
    ).update(
        is_read=True,
        read_at=timezone.now()
    )

    messages = conversation.messages.select_related('sender').order_by('created_at')

    data = []
    for message in messages:
        data.append({
            'id': message.id,
            'text': message.text,
            'sender_id': message.sender.id,
            'sender_name': f"{message.sender.first_name} {message.sender.last_name}",
            'sender_email': message.sender.email,
            'is_read': message.is_read,
            'created_at': timezone.localtime(message.created_at).strftime("%d %b %Y, %I:%M %p"),
            'read_at': timezone.localtime(message.read_at).strftime("%d %b %Y, %I:%M %p") if message.read_at else '',
        })

    return JsonResponse({'messages': data}) 
