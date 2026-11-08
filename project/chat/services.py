from .models import Conversation


def get_or_create_direct_conversation(user_a, user_b):
    """
    คืนห้องแชทระหว่าง user_a กับ user_b (สร้างใหม่ถ้ายังไม่มี)
    ใช้ร่วมกันทั้งตอนกดปุ่ม Chat และตอนที่ Match กันสำเร็จ
    """
    conversation = (
        Conversation.objects.filter(participants=user_a)
        .filter(participants=user_b)
        .first()
    )
    if conversation is None:
        conversation = Conversation.objects.create()
        conversation.participants.add(user_a, user_b)
    return conversation
