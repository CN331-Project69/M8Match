"""
สร้างห้องแชทให้คู่ที่ Match กันไปแล้วแต่ยังไม่มีห้อง
(ก่อนหน้านี้ห้องจะเกิดก็ต่อเมื่อกดปุ่ม Chat ใน popup เท่านั้น)
"""

from django.db import migrations


def backfill_match_conversations(apps, schema_editor):
    Match = apps.get_model("matching", "Match")
    Conversation = apps.get_model("chat", "Conversation")

    for match in Match.objects.all().iterator():
        exists = (
            Conversation.objects.filter(participants=match.user1_id)
            .filter(participants=match.user2_id)
            .exists()
        )
        if not exists:
            conversation = Conversation.objects.create()
            conversation.participants.add(match.user1_id, match.user2_id)


class Migration(migrations.Migration):
    dependencies = [
        ("matching", "0003_project_required_categories_project_team_categories"),
        ("chat", "0001_initial"),
    ]

    operations = [
        # ย้อน migration ได้โดยไม่ลบห้องแชท (อาจมีข้อความอยู่แล้ว)
        migrations.RunPython(backfill_match_conversations, migrations.RunPython.noop),
    ]
