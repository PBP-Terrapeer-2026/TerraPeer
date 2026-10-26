from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class BootstrapAuthMixin:
    """Adds Bootstrap classes, autocomplete hints and invalid states to auth forms."""

    autocomplete = {}
    placeholders = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if name in self.autocomplete:
                field.widget.attrs['autocomplete'] = self.autocomplete[name]
            if name in self.placeholders:
                field.widget.attrs['placeholder'] = self.placeholders[name]

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                attrs = self.fields[name].widget.attrs
                attrs['class'] = 'form-control is-invalid'
                attrs['aria-invalid'] = 'true'
                attrs['aria-describedby'] = f'{name}-error'


class LoginForm(BootstrapAuthMixin, AuthenticationForm):
    autocomplete = {'username': 'username', 'password': 'current-password'}
    placeholders = {'username': 'Your username', 'password': 'Your password'}


class RegisterForm(BootstrapAuthMixin, UserCreationForm):
    autocomplete = {'username': 'username', 'password1': 'new-password', 'password2': 'new-password'}
    placeholders = {'username': 'Choose a username'}
