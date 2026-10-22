from django import forms
from .models import GardenJournalEntry


class GardenJournalEntryForm(forms.ModelForm):
    class Meta:
        model = GardenJournalEntry
        fields = [
            "plant_name",
            "entry_date",
            "entry_type",
            "title",
            "notes",
            "harvest_quantity",
            "harvest_unit",
            "weather_summary",
        ]

        widgets = {
            "entry_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={"rows": 4}
            ),
            "harvest_quantity": forms.NumberInput(
                attrs={"min": "0", "step": "0.01"}
            ),
        }

        labels = {
            "plant_name": "Plant Name",
            "entry_date": "Entry Date",
            "entry_type": "Milestone Type",
            "title": "Title",
            "notes": "Progress Notes",
            "harvest_quantity": "Harvest Quantity",
            "harvest_unit": "Harvest Unit",
            "weather_summary": "Weather Conditions",
        }
