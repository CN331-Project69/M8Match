from django.contrib import admin
from .models import Conversation, Message

# นำ Model มาลงทะเบียนเพื่อให้แสดงในหน้า Admin
admin.site.register(Conversation)
admin.site.register(Message)