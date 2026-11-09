from django import forms
from django.core.exceptions import ValidationError

from .models import Post, PostImage


# กำหนดข้อจำกัดของโพสและรูปภาพ
MAX_TITLE_LENGTH = 200
MAX_POST_LENGTH = 2000
MAX_IMAGE_COUNT = 3
MAX_IMAGE_SIZE = 5 * 1024 * 1024


# Input ที่รองรับการเลือกรูปภาพหลายไฟล์
class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


# Field สำหรับตรวจสอบรูปภาพหลายไฟล์
class MultipleImageField(forms.ImageField):
    widget = MultipleImageInput

    def clean(self, data, initial=None):
        if not data:
            return []

        if isinstance(data, (list, tuple)):
            return [
                forms.ImageField.clean(self, image, initial)
                for image in data
            ]

        return [
            forms.ImageField.clean(self, data, initial)
        ]


# Form สำหรับสร้างโพสและแก้ไขโพส
class PostForm(forms.ModelForm):

    # ช่องสำหรับอัปโหลดรูปภาพใหม่
    images = MultipleImageField(
        required=False,
        widget=MultipleImageInput(attrs={
            "multiple": True,
            "accept": "image/*"
        })
    )

    class Meta:
        model = Post
        fields = ["title", "content", "categories"]

        widgets = {
            "title": forms.TextInput(attrs={
                "maxlength": MAX_TITLE_LENGTH,
                "placeholder": "Post title..."
            }),
            "content": forms.Textarea(attrs={
                "rows": 4,
                "maxlength": MAX_POST_LENGTH,
                "placeholder": "Share something with your team..."
            }),
            # สามารถเลือก Category ได้หลายหมวด
            "categories": forms.SelectMultiple(),
        }

    # ตรวจสอบหัวข้อโพส
    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()

        if not title:
            raise ValidationError(
                "Post title cannot be empty."
            )

        if len(title) > MAX_TITLE_LENGTH:
            raise ValidationError(
                f"Post title cannot exceed {MAX_TITLE_LENGTH} characters."
            )

        return title

    # ตรวจสอบเนื้อหาโพส
    def clean_content(self):
        content = self.cleaned_data.get("content", "").strip()

        if not content:
            raise ValidationError(
                "Post content cannot be empty."
            )

        if len(content) > MAX_POST_LENGTH:
            raise ValidationError(
                f"Post content cannot exceed {MAX_POST_LENGTH} characters."
            )

        return content

    # ตรวจสอบขนาดของรูปภาพแต่ละไฟล์
    def clean_images(self):
        images = self.cleaned_data.get("images", [])

        for image in images:
            if image.size > MAX_IMAGE_SIZE:
                raise ValidationError(
                    "Each image must be smaller than 5 MB."
                )

        return images

    # ตรวจสอบจำนวนรูปทั้งหมดหลังจากเพิ่มและลบรูป
    def clean(self):
        cleaned_data = super().clean()

        new_images = cleaned_data.get("images", [])
        deleted_images = cleaned_data.get("delete_images", [])

        # นับรูปเดิมของโพส (ถ้าเป็นการแก้ไข)
        if self.instance and self.instance.pk:
            existing_count = self.instance.images.count()
        else:
            existing_count = 0

        # จำนวนรูปหลังจากลบรูปเดิมและเพิ่มรูปใหม่
        final_count = (
            existing_count
            - len(deleted_images)
            + len(new_images)
        )

        if final_count > MAX_IMAGE_COUNT:
            self.add_error(
                "images",
                ValidationError(
                    f"A post can have up to {MAX_IMAGE_COUNT} images in total."
                )
            )

        return cleaned_data


# Form สำหรับแก้ไขโพสและเลือกลบรูปเดิม
class PostEditForm(PostForm):

    # เลือกรูปเดิมที่ต้องการลบได้หลายรูป
    delete_images = forms.ModelMultipleChoiceField(
        queryset=PostImage.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # จำกัดตัวเลือกให้เห็นเฉพาะรูปของโพสที่กำลังแก้ไข
        if self.instance and self.instance.pk:
            self.fields["delete_images"].queryset = (
                self.instance.images.all()
            )
