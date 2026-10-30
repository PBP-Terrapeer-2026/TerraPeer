from django import forms
import re

from .models import Pot
from django.utils.html import strip_tags


ACTIVE_HTML_CONTENT = re.compile(
    r"<(script|style|iframe|object|embed|svg|math)\b[^>]*>.*?</\1\s*>|"
    r"<(script|style|iframe|object|embed|svg|math)\b[^>]*/\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)



class PotForm(forms.ModelForm):

    MATERIAL_CHOICES = [
        ("plastik", "Plastik"),
        ("terakota", "Terakota"),
        ("keramik glazed", "Keramik glazed"),
        ("kayu/plastik", "Kayu/plastik"),
    ]

    material = forms.ChoiceField(
        label="Bahan pot",
        choices=MATERIAL_CHOICES,
        widget=forms.Select(attrs={"class": "form-select", "id": "pot-material-input"}),
    )
    size_cm = forms.IntegerField(
        label="Ukuran (cm)",
        min_value=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control flex-grow-1",
            "id": "pot-size-input",
            "min": 1,
            "placeholder": "Ukuran (cm)",
        }),
    )

    class Meta:
        model = Pot
        fields = ("name", "size_cm", "material")
        labels = {
            "name": "Nama pot",
            "size_cm": "Ukuran (cm)",
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control flex-grow-1",
                "id": "pot-name-input",
                "placeholder": "Nama pot",
            }),
        }

    def clean_name(self):
        raw_name = ACTIVE_HTML_CONTENT.sub("", self.cleaned_data["name"])
        name = strip_tags(raw_name).strip()
        if not name:
            raise forms.ValidationError("Nama pot tidak boleh kosong.")
        return name

