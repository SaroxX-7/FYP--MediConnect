from django.urls import path

from . import views

urlpatterns = [
    path("start/<int:appointment_id>/", views.start_chat, name="start_chat"),
   # path("room/<int:conversation_id>/", views.chat_room, name="chat_room"),
    path("conversation/<int:conversation_id>/messages/", views.conversation_messages, name="conversation_messages"),
]
