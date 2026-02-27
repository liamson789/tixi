from django import forms
from raffles.models import Raffle, HomeCarouselSlide


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]

        cleaned = []
        errors = []
        for item in data:
            try:
                cleaned.append(super().clean(item, initial))
            except forms.ValidationError as exc:
                errors.extend(exc.error_list)

        if errors:
            raise forms.ValidationError(errors)

        return cleaned

class RaffleForm(forms.ModelForm):
    class Meta:
        model = Raffle
        fields = [
            'title',
            'description',
            'price_per_number',
            'draw_date',
            'min_sales_percentage',
            'is_active'
        ]
        widgets = {
            'draw_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['draw_date'].input_formats = [
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%d %H:%M:%S',
        ]

        if self.instance and self.instance.pk and self.instance.draw_date:
            self.initial['draw_date'] = self.instance.draw_date.strftime('%Y-%m-%dT%H:%M')


class RaffleCreateForm(RaffleForm):
    list_name = forms.CharField(max_length=100)
    list_start = forms.IntegerField(min_value=0)
    list_end = forms.IntegerField(min_value=0)
    media_files = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={'multiple': True})
    )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('list_start')
        end = cleaned_data.get('list_end')

        if start is not None and end is not None and start > end:
            self.add_error('list_end', 'El numero final debe ser mayor o igual al inicial.')

        return cleaned_data


class RaffleEditForm(RaffleForm):
    media_files = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={'multiple': True})
    )


class CarouselSlideForm(forms.ModelForm):
    class Meta:
        model = HomeCarouselSlide
        fields = ['title', 'subtitle', 'image', 'link_url', 'display_order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'link_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://... (opcional)'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    