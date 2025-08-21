from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Report

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username")
    password = forms.CharField(widget=forms.PasswordInput)


class RegistrationForm(forms.ModelForm):
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
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email", "role", "skills", "password1", "password2"]

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two password fields must match.")
        role = cleaned_data.get("role")
        if role != "volunteer":
            cleaned_data["skills"] = ""
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


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
