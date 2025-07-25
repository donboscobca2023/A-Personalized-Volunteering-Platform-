# Generated by Django 5.2.1 on 2025-06-18 16:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("feeds", "0002_application"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="application",
            name="review",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="application",
            name="review_rating",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="application",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("completed", "Completed"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
