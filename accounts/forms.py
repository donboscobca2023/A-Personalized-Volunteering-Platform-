from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Report

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username")
    password = forms.CharField(widget=forms.PasswordInput)


class RegistrationForm(UserCreationForm):
    ROLE_CHOICES = (
        ("volunteer", "Volunteer"),
        ("ngo", "NGO"),
        ("admin", "Admin"),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    skills = forms.CharField(
        required=False,
        label="Skills (optional)",
        help_text="Comma-separated skills (e.g. Python, Fundraising, Event Planning)",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Python, Fundraising, Event Planning"}),
    )

    class Meta:
        model = User
        fields = ["username", "email", "role", "skills", "password1", "password2"]

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        if role != "volunteer":
            cleaned_data["skills"] = ""
        return cleaned_data


class EditAccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "skills"]
        widgets = {
            "skills": forms.TextInput(attrs={"placeholder": "e.g. Python, Fundraising, Event Planning"}),
        }


class ReviewForm(forms.ModelForm):
    review = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Review")
    review_rating = forms.IntegerField(min_value=1, max_value=5, required=False, label="Rating (1-5)")

    class Meta:
        model = get_user_model()._meta.get_field('id').model._meta.get_field('id').model._meta.apps.get_model('feeds', 'Application')
        fields = ["review", "review_rating"]


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["reason"]
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 3, "placeholder": "Describe the issue..."}),
        }
