from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile
from django import forms

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_picture', 'display_name', 'about_me', 'skills']
        widgets = {
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'display_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อที่จะให้เพื่อนร่วมทีมเห็น'}),
            'about_me': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'แนะนำตัวเองสั้นๆ เป้าหมายใน Hackathon...'}),
            'skills': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ระบุทักษะที่มี...'}),
        }