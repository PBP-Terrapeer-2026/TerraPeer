
from django import forms

from my_plants.models import Plant
from .models import GardenJournalEntry


class GardenJournalEntryForm(forms.ModelForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        # Only show plants owned by the currently logged-in user.
        self.fields["plant"].queryset = (
            Plant.objects.for_user(user).order_by("name", "pk")
        )

        # A plant is required when creating or editing a journal entry.
        self.fields["plant"].required = True
        self.fields["plant"].empty_label = "Select a plant"

    class Meta:
        model = GardenJournalEntry

        fields = [
            "plant",
            "entry_date",
            "entry_type",
            "title",
            "notes",
            "harvest_quantity",
            "harvest_unit",
            "weather_condition",
            "weather_summary",
        ]

        widgets = {
            "plant": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "entry_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "entry_type": forms.RadioSelect(
                attrs={"class": "journal-form-v2__event-input"}
            ),
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
            "weather_condition": forms.RadioSelect(
                attrs={
                    "class": "journal-form-v2__weather-input",
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
            "plant": "Plant",
            "entry_date": "Entry date",
            "entry_type": "Milestone type",
            "title": "Title",
            "notes": "Progress notes",
            "harvest_quantity": "Harvest quantity",
            "harvest_unit": "Harvest unit",
            "weather_condition": "Weather condition",
            "weather_summary": "Additional weather notes",
        }

        help_texts = {
            "plant": "Select a plant from your My Plants collection.",
            "notes": "Describe the changes, progress, or problems you noticed.",
            "harvest_unit": "For example: grams, kilograms, pieces, or bunches.",
            "weather_condition": "Select the weather condition you observed.",
            "weather_summary": "Optional. Add details about the weather, if needed.",
        }

    def save(self, commit=True):
        entry = super().save(commit=False)

        # Keep the plant name as a snapshot for historical journal display.
        entry.plant_name = entry.plant.name

        if commit:
            entry.save()
            self.save_m2m()

        return entry

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
