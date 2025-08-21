from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ("volunteer", "Volunteer"),
        ("ngo", "NGO"),
        ("admin", "Admin"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="volunteer")
    skills = models.CharField(max_length=255, blank=True, help_text="Comma-separated skills (e.g. Python, Fundraising, Event Planning)")
    is_approved = models.BooleanField(default=True, help_text="Admin approval required for NGOs")

    def __str__(self):
        return f"{self.username} ({self.role})"


class Report(models.Model):
    REPORT_TYPE_CHOICES = (
        ("user", "User"),
        ("ngo", "NGO"),
    )
    reporter = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reports_made')
    reported = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reports_received')
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)
    handled_by = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='reports_handled')
    handled_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True)

    def __str__(self):
        return f"Report by {self.reporter} on {self.reported} ({self.report_type})"
