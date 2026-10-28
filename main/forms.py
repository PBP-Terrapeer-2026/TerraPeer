
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
            "plant_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Tomato 1",
                    "autocomplete": "off",
                }
            ),
            "entry_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "entry_type": forms.RadioSelect(attrs={"class": "journal-form-v2__event-input"}),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Give this moment a title",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe what you observed...",
                }
            ),
            "harvest_quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "e.g. 140",
                }
            ),
            "harvest_unit": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. grams, pieces, bunches",
                }
            ),
            "weather_summary": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Sunny, cloudy, light rain",
                    "maxlength": 200,
                }
            ),
        }

        labels = {
            "plant_name": "Plant",
            "entry_date": "Entry date",
            "entry_type": "Milestone type",
            "title": "Title",
            "notes": "Progress notes",
            "harvest_quantity": "Harvest quantity",
            "harvest_unit": "Harvest unit",
            "weather_summary": "Weather conditions",
        }

        help_texts = {
            "plant_name": "Enter the plant name for this entry.",
            "notes": "Describe the changes, progress, or problems you noticed.",
            "harvest_unit": "For example: grams, kilograms, pieces, or bunches.",
            "weather_summary": "Optional. Record the weather you observed.",
        }

    def clean(self):
        cleaned_data = super().clean()

        entry_type = cleaned_data.get("entry_type")
        harvest_quantity = cleaned_data.get("harvest_quantity")

        if entry_type == "harvest":
            if harvest_quantity is None:
                self.add_error(
                    "harvest_quantity",
                    "Enter the quantity harvested for this entry.",
                )
            elif harvest_quantity < 0:
                self.add_error(
                    "harvest_quantity",
                    "Harvest quantity cannot be negative.",
                )
        else:
            # A non-harvest entry should not retain harvest details
            # when a user changes an existing entry's milestone type.
            cleaned_data["harvest_quantity"] = None
            cleaned_data["harvest_unit"] = ""

        return cleaned_data
