from django import forms

from .models import UserProfile


class UserProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        is_google_profile = kwargs.pop('is_google_profile', False)
        super().__init__(*args, **kwargs)

        if is_google_profile:
            self.fields['full_name'].disabled = True
            self.fields['avatar_url'].disabled = True

    class Meta:
        model = UserProfile
        fields = ['full_name', 'avatar_url', 'contact_phone']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre completo'}),
            'avatar_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+57 300 123 4567'}),
        }
