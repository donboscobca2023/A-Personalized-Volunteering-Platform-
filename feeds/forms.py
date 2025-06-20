from django import forms
from .models import Opportunity


class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = [
            "title",
            "description",
            "location",
            "start_date",
            "end_date",
            "skills_required",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }
