from django import forms
from django.utils import timezone

from .models import Plant, PlantCheckIn
from .photos import ACCEPT, process_photo


class BootstrapFormMixin:
    """Adds Bootstrap 5 classes to widgets and marks invalid fields for screen readers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.HiddenInput, forms.RadioSelect, forms.CheckboxInput)):
                continue
            base = 'form-select' if isinstance(widget, forms.Select) else 'form-control'
            widget.attrs['class'] = f"{base} {widget.attrs.get('class', '')}".strip()

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                attrs = self.fields[name].widget.attrs
                if 'is-invalid' not in attrs.get('class', ''):
                    attrs['class'] = f"{attrs.get('class', '')} is-invalid".strip()
                attrs['aria-invalid'] = 'true'
                attrs['aria-describedby'] = f'{self.add_prefix(name)}-error'


PHOTO_HELP = 'JPG, PNG or WebP, up to 5 MB. Location data is removed before saving.'


def photo_field(required=False, label='Photo'):
    return forms.FileField(required=required, label=label, help_text=PHOTO_HELP,
                           widget=forms.FileInput(attrs={'accept': ACCEPT, 'data-photo-input': ''}))


class PhotoCleanMixin:
    """Validates the `photo` upload and keeps the processed JPEG on `self.processed_photo`."""

    processed_photo = None

    def clean_photo(self):
        upload = self.cleaned_data.get('photo')
        if upload:
            self.processed_photo = process_photo(upload)
        return upload


class PlantForm(PhotoCleanMixin, BootstrapFormMixin, forms.ModelForm):
    photo = photo_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['planted_on'].widget.attrs['max'] = timezone.localdate().isoformat()
        if self.instance.pk:
            self.fields['photo'].label = 'Add a new photo'
            self.fields['photo'].help_text = 'Optional. It is added to the photo diary. ' + PHOTO_HELP

    class Meta:
        model = Plant
        fields = ['name', 'species_name', 'planted_on', 'growth_stage', 'notes', 'perenual_species_id']
        labels = {
            'name': 'Nickname', 'species_name': 'Species',
            'planted_on': 'Planted on', 'growth_stage': 'Growth stage',
            'notes': 'Notes',
        }
        help_texts = {
            'name': "Names don't have to be unique, e.g. Tomato 1.",
            'planted_on': 'The planting date cannot be in the future.',
            'notes': 'Where you got it, anything worth remembering. Up to 2000 characters.',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Balcony tomato'}),
            'species_name': forms.TextInput(attrs={'placeholder': 'e.g. Cherry Tomato'}),
            'planted_on': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Anything you want to remember about this plant.'}),
            'perenual_species_id': forms.HiddenInput(),
        }


class StageForm(PhotoCleanMixin, BootstrapFormMixin, forms.ModelForm):
    """Changing the stage requires a photo of the plant at its new stage."""

    photo = photo_field(label='Photo of the plant now')
    caption = forms.CharField(required=False, max_length=200, label='Caption (optional)',
                              widget=forms.TextInput(attrs={'placeholder': 'e.g. First flowers opened'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_stage = self.instance.growth_stage

    @property
    def stage_changed(self):
        return self.cleaned_data.get('growth_stage', self.original_stage) != self.original_stage

    def clean(self):
        cleaned = super().clean()
        if self.stage_changed and not cleaned.get('photo') and 'photo' not in self.errors:
            self.add_error('photo', 'Add a photo of the plant at its new stage.')
        return cleaned

    class Meta:
        model = Plant
        fields = ['growth_stage']
        labels = {'growth_stage': 'Growth stage'}


class PhotoForm(PhotoCleanMixin, BootstrapFormMixin, forms.Form):
    photo = photo_field(required=True, label='Photo')
    caption = forms.CharField(required=False, max_length=200, label='Caption (optional)',
                              widget=forms.TextInput(attrs={'placeholder': 'What changed?'}))


class PlantFilterForm(BootstrapFormMixin, forms.Form):
    SORT_CHOICES = [
        ('newest', 'Recently added'), ('oldest', 'Oldest first'),
        ('name', 'Name A–Z'), ('planted', 'Longest growing'),
    ]
    STATUS_CHOICES = [('', 'All'), ('active', 'Active'), ('finished', 'Finished')]

    q = forms.CharField(required=False, max_length=120, label='Search',
                        widget=forms.TextInput(attrs={'placeholder': 'Name or species, e.g. Tomato', 'type': 'search'}))
    stage = forms.ChoiceField(required=False, label='Growth stage',
                              choices=[('', 'All stages'), *Plant.Stage.choices])
    status = forms.ChoiceField(required=False, label='Status', choices=STATUS_CHOICES, widget=forms.RadioSelect)
    sort = forms.ChoiceField(required=False, label='Sort by', choices=SORT_CHOICES)

    ORDERING = {
        'newest': ['-created_at', '-pk'], 'oldest': ['created_at', 'pk'],
        'name': ['name', 'pk'], 'planted': ['planted_on', 'pk'],
    }

class CheckInForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['condition'].choices = PlantCheckIn.Condition.choices  # no blank "-----" chip

    class Meta:
        model = PlantCheckIn
        fields = ['condition', 'note']
        labels = {'condition': 'How does it look today?', 'note': 'Note (optional)'}
        widgets = {
            'condition': forms.RadioSelect,
            'note': forms.TextInput(attrs={'placeholder': 'e.g. Lower leaves look pale', 'maxlength': 200}),
        }
