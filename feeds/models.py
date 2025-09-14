from django.db import models
from django.conf import settings


class Opportunity(models.Model):
    ngo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "ngo"},
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    skills_required = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Application(models.Model):
    volunteer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "volunteer"},
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="applications"
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("completed", "Completed"),
        ],
        default="pending",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    review = models.TextField(blank=True)
    review_rating = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("volunteer", "opportunity")  # prevent duplicate applications


# Task model for assigning tasks to approved applicants
class Task(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for {self.application.volunteer}" 
