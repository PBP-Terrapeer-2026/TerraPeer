from django import forms
from .models import GrowingSpace

class GrowingSpaceForm(forms.ModelForm):
    class Meta:
        model = GrowingSpace
        
        fields = [
            "name",
            "environment",
            "space_type",
            "other_space_type",
            "city",
            "geocoding_id",
            "region",
            "country",
            "latitude",
            "longitude",
            "timezone",
            "sunlight_range",
            "light_exposure",
            "growing_medium",
            "rain_access",
            "support_available",
            "pot_capacity",
            "care_availability",
            "notes",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "e.g. My Balcony",
                "maxlength": 60,
            }),

            "city": forms.TextInput(attrs={
                "placeholder": "Search for a city...",
                "autocomplete": "off",
            }),

            "other_space_type": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Please specify",
                    "maxlength": "60",
                    "aria-label": "Please specify the space type",
                }
            ),

            "geocoding_id": forms.HiddenInput(),
            "region": forms.HiddenInput(),
            "country": forms.HiddenInput(),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "timezone": forms.HiddenInput(),

            "pot_capacity": forms.NumberInput(attrs={
                "min": 1,
                "max": 100,
                "placeholder": "e.g. 4",
            }),

            "notes": forms.Textarea(attrs={
                "rows": 4,
                "maxlength": 500,
                "placeholder": (
                    "Additional details about your growing space..."
                ),
            }),
        }

        labels = {
            "name": "Growing Space Name",
            "environment": "Environment",
            "space_type": "Space Type",
            "city": "City or Area",
            "sunlight_range": "Daily Sunlight",
            "light_exposure": "Light Exposure",
            "growing_medium": "Growing Medium",
            "rain_access": "Rain Access",
            "support_available": "Plant Support Available",
            "pot_capacity": "Pot Capacity",
            "care_availability": "Care Availability",
            "notes": "Additional Notes",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["space_type"].choices = [
            (value, label)
            for value, label in self.fields["space_type"].choices
            if value != GrowingSpace.SpaceType.ROOM
        ]

        for field in self.fields.values():
            widget = field.widget

            if isinstance(widget, forms.HiddenInput):
                continue

            if isinstance(widget, forms.Select):
                css_class = "form-select"
            else:
                css_class = "form-control"

            existing_class = widget.attrs.get("class", "")

            widget.attrs["class"] = (
                f"{existing_class} {css_class}".strip()
            )

    def clean(self):
        cleaned_data = super().clean()

        space_type = cleaned_data.get("space_type")
        other_type = (cleaned_data.get("other_space_type") or "").strip()

        if space_type == GrowingSpace.SpaceType.OTHER:
            if not other_type:
                self.add_error(
                    "other_space_type",
                    "Please specify the space type.",
                )
            else:
                cleaned_data["other_space_type"] = other_type
        else:
            cleaned_data["other_space_type"] = ""

        return cleaned_data

