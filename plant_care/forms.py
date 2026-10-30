from datetime import timedelta
from django import forms
from .models import CareTask, PlantCareSpace, LegacyPlant
from my_plants.models import Plant
from garden_setup.models import GrowingSpace

TITLES = {
    "Watering": "Check soil moisture",
    "Fertilizing": "Feed with diluted fertilizer",
    "Pruning": "Trim yellow leaves",
    "Inspection": "Check leaf condition",
    "Repotting": "Move to a larger pot",
}


class CareTaskForm(forms.ModelForm):
    repeat = forms.ChoiceField(
        choices=[("none", "Does not repeat"), ("every", "Every N days")]
    )
    interval = forms.IntegerField(
        required=False,
        min_value=1,
        label="Interval (days)",
        widget=forms.NumberInput(attrs={"step": 1, "min": 1}),
    )

    class Meta:
        model = CareTask
        fields = ["action_type", "due_date", "instructions"]
        labels = {
            "action_type": "Action Type",
            "due_date": "Start Date",
            "instructions": "Instructions (optional)",
        }
        widgets = {
            "due_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "instructions": forms.Textarea(
                attrs={"rows": 3, "placeholder": "What should you check or do?"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_action = self.instance.action_type
        self.fields["action_type"].choices = [
            ("", "Choose an action")
        ] + CareTask.ACTIONS
        self.initial.update(
            repeat="every" if self.instance.repeat_every else "none",
            interval=self.instance.repeat_every,
        )
        for name, field in self.fields.items():
            field.widget.attrs["aria-describedby"] = "error-" + name

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("repeat") == "every":
            n = cleaned.get("interval")
            if n is None and "interval" not in self.errors:
                self.add_error("interval", "Enter a whole number of at least 1.")
            if n and cleaned.get("due_date"):
                try:
                    cleaned["due_date"] + timedelta(days=n)
                except OverflowError:
                    self.add_error(
                        "interval",
                        "This interval exceeds the supported calendar range.",
                    )
        return cleaned

    def save(self, commit=True):
        task = super().save(commit=False)
        task.repeat_every = (
            self.cleaned_data["interval"]
            if self.cleaned_data["repeat"] == "every"
            else None
        )
        if not task.title or self._original_action != task.action_type:
            task.title = TITLES[task.action_type]
        if commit:
            task.save()
        return task


class PlantCareSpaceForm(forms.ModelForm):
    class Meta:
        model = PlantCareSpace
        fields = ["growing_space"]
        labels = {"growing_space": "Weather location"}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["growing_space"].queryset = GrowingSpace.objects.filter(user=user)
        self.fields["growing_space"].empty_label = "Select a growing space"


class LegacyPlantLinkForm(forms.Form):
    legacy_plant = forms.ModelChoiceField(
        queryset=LegacyPlant.objects.none(), label="Previous care plant"
    )
    plant = forms.ModelChoiceField(
        queryset=Plant.objects.none(), label="Plant in My Plants"
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["legacy_plant"].queryset = LegacyPlant.objects.filter(
            garden__owner=user,
            care_tasks__plant__isnull=True,
            care_tasks__isnull=False,
        ).distinct()
        self.fields["plant"].queryset = Plant.objects.for_user(user)
