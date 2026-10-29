from django import forms

from .models import Pot


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

