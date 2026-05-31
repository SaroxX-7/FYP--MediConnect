import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone

from chat.models import Conversation, Message


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"

        if not self.user.is_authenticated:
            self.close()
            return

        try:
            self.conversation = Conversation.objects.select_related(
                "appointment__doctor__user",
                "appointment__patient"
            ).get(id=self.conversation_id)
        except Conversation.DoesNotExist:
            self.close()
            return

        appointment = self.conversation.appointment

        if self.user != appointment.patient and self.user != appointment.doctor.user:
            self.close()
            return

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

        self.mark_messages_as_seen()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def format_datetime(self, dt):
        if not dt:
            return ""

        return timezone.localtime(dt).strftime("%d %b %Y, %I:%M %p")

    def receive(self, text_data):
        if not self.user.is_authenticated:
            return

        text_data_json = json.loads(text_data)
        action = text_data_json.get("action", "message")

        if action == "message":
            message_text = text_data_json.get("message", "").strip()

            if not message_text:
                return

            message = Message.objects.create(
                conversation=self.conversation,
                sender=self.user,
                text=message_text
            )

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message_id": message.id,
                    "message": message.text,
                    "sender_email": self.user.email,
                    "sender_id": self.user.id,

                    # Uses TIME_ZONE from settings.py
                    "created_at": self.format_datetime(message.created_at),

                    "is_read": message.is_read,
                    "read_at": "",
                }
            )

        elif action == "mark_seen":
            self.mark_messages_as_seen()

    def mark_messages_as_seen(self):
        unread_messages = Message.objects.filter(
            conversation=self.conversation,
            is_read=False
        ).exclude(sender=self.user)

        unread_ids = list(unread_messages.values_list("id", flat=True))

        if not unread_ids:
            return

        seen_time = timezone.now()

        unread_messages.update(
            is_read=True,
            read_at=seen_time
        )

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "seen_update",
                "message_ids": unread_ids,
                "seen_by_user_id": self.user.id,

                # Uses TIME_ZONE from settings.py
                "read_at": self.format_datetime(seen_time),
            }
        )

    def chat_message(self, event):
        self.send(text_data=json.dumps({
            "event_type": "message",
            "message_id": event["message_id"],
            "message": event["message"],
            "sender_email": event["sender_email"],
            "sender_id": event["sender_id"],
            "created_at": event["created_at"],
            "is_read": event["is_read"],
            "read_at": event["read_at"],
        }))

    def seen_update(self, event):
        self.send(text_data=json.dumps({
            "event_type": "seen_update",
            "message_ids": event["message_ids"],
            "seen_by_user_id": event["seen_by_user_id"],
            "read_at": event["read_at"],
        }))
