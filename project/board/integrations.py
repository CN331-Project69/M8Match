from abc import ABC, abstractmethod

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string


class BoardIntegrationAdapter(ABC):
    """
    สัญญาการเชื่อมต่อระหว่าง Board กับระบบของสมาชิกคนอื่น

    ผู้รับผิดชอบรวม Backend จะสร้าง Adapter ที่สืบทอดจาก Class นี้
    แล้วเชื่อมต่อกับ Model, View และ Service ของแต่ละระบบจริง
    """

    @abstractmethod
    def get_post_interaction_data(self, posts, user):
        """
        ดึงข้อมูล Like และ Comment ของหลาย Post พร้อมกัน

        รูปแบบข้อมูลที่ต้องส่งกลับ:
        {
            post_id: {
                "like_count": 10,
                "comment_count": 5,
                "is_liked": True
            }
        }

        ข้อกำหนด:
        - ดึงข้อมูลหลาย Post พร้อมกัน เพื่อลดปัญหา N+1 Queries
        - Guest เห็นได้เฉพาะจำนวน Like และ Comment
        - ห้ามส่งเนื้อหา Comment ผ่านฟังก์ชันนี้
        - is_liked ของ Guest ต้องเป็น False
        - จำนวน Like และ Comment ต้องมาจากข้อมูลจริง
        """

    @abstractmethod
    def toggle_like(self, post, user):
        """
        เพิ่ม Like หรือยกเลิก Like

        ผลลัพธ์:
        {
            "liked": True,
            "like_count": 11
        }

        ต้องตรวจสอบการ Login และป้องกัน Like ซ้ำใน Backend
        """

    @abstractmethod
    def get_liked_posts(self, user):
        """
        ดึงรายการ Post ที่ผู้ใช้กด Like ไว้

        ข้อกำหนด:
        - คืนค่าเป็นรายการ Post ของ Board
        - เรียงจาก Like ล่าสุดไปเก่าสุด
        - ไม่คืน Post ที่ถูกซ่อน
        - ต้องดึงข้อมูลโดยไม่เกิด N+1 Queries
        - ไม่สร้าง Like Model ซ้ำในแอป Board
        """

    @abstractmethod
    def get_comments(self, post, user):
        """
        ดึง Comment ของ Post

        อนุญาตเฉพาะผู้ใช้ที่ Login แล้ว
        Guest ห้ามได้รับเนื้อหา Comment จาก Backend
        """

    @abstractmethod
    def create_comment(self, post, user, content):
        """
        บันทึก Comment ใหม่หลังผ่าน Moderation แล้ว

        ต้องตรวจสอบสิทธิ์และเนื้อหาว่างก่อนบันทึก
        ไม่ต้องเรียก Moderation ซ้ำ เพราะ View
        จะตรวจสอบผ่าน moderate_comment() ก่อนแล้ว
        """

    @abstractmethod
    def submit_post_report(self, post_id, user, reason):
        """
        ส่งรายงาน Post

        ต้องตรวจสอบสิทธิ์และกฎการรายงานซ้ำ
        การ Report ไม่ทำให้ Post ถูกซ่อนโดยอัตโนมัติ
        """

    @abstractmethod
    def submit_comment_report(self, comment, user, reason):
        """
        ส่งรายงาน Comment

        ต้องตรวจสอบสิทธิ์และกฎการรายงานซ้ำ
        """

    @abstractmethod
    def moderate_post(self, title, content, user):
        """
        ตรวจสอบ Title และ Content ก่อนบันทึก Post

        รูปแบบผลลัพธ์:
        {
            "is_allowed": True,
            "errors": {},
            "warnings": {}
        }

        หากไม่ผ่าน ต้องปฏิเสธการบันทึกและส่งเหตุผลกลับมา
        ลิงก์น่าสงสัยให้แจ้งเตือน แต่ยังอนุญาตให้โพสต์ได้
        """

    @abstractmethod
    def moderate_comment(self, content, user):
        """
        ตรวจสอบ Comment ก่อนบันทึก

        ใช้รูปแบบผลลัพธ์เดียวกับ moderate_post
        """

    @abstractmethod
    def get_public_profile_url(self, user):
        """
        คืน URL ของหน้า Public Profile

        หากยังไม่มี URL ให้คืน None
        Board ไม่รับผิดชอบสร้างหน้า Profile หรือระบบ Chat
        """

    @abstractmethod
    def get_liked_posts(self, user):
        """
        ดึงรายการ Post ที่ผู้ใช้กด Like ไว้

        ข้อกำหนด:
        - คืนค่าเป็นรายการ Post ของ Board
        - เรียงจาก Like ล่าสุดไปเก่าสุด
        - ไม่คืน Post ที่ถูกซ่อน
        - ต้องดึงข้อมูลโดยไม่เกิด N+1 Queries
        - ไม่สร้าง Like Model ซ้ำในแอป Board
        """

    @abstractmethod
    def get_comment_for_report(self, comment_id):
        """
        ค้นหา Comment จริงจาก ID
        คืนค่า Comment object หรือ None หากไม่พบ
        """


def get_board_adapter(required=False):
    """
    โหลด Adapter ที่ตั้งค่าไว้ใน settings.py

    required=False:
        หากยังไม่ได้เชื่อมระบบเพื่อน ให้คืน None

    required=True:
        หากไม่มี Adapter ให้แจ้ง Configuration Error
    """

    adapter_path = getattr(
        settings,
        "BOARD_INTEGRATION_ADAPTER",
        None
    )

    if not adapter_path:
        if required:
            raise ImproperlyConfigured(
                "BOARD_INTEGRATION_ADAPTER has not been configured."
            )

        return None

    try:
        adapter_class = import_string(adapter_path)

    except (ImportError, AttributeError) as error:
        raise ImproperlyConfigured(
            "Cannot import BOARD_INTEGRATION_ADAPTER. "
            "Please check its Python import path."
        ) from error

    if (
        not isinstance(adapter_class, type)
        or not issubclass(adapter_class, BoardIntegrationAdapter)
    ):
        raise ImproperlyConfigured(
            "BOARD_INTEGRATION_ADAPTER must inherit "
            "from BoardIntegrationAdapter."
        )

    return adapter_class()