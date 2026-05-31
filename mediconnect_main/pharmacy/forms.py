from django import forms
from django.forms import inlineformset_factory

from .models import Medicine, Prescription, PrescriptionItem


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            'name',
            'generic_name',
            'dosage_form',
            'strength',
            'unit_price',
            'stock_qty',
            'is_active',
            'description',
            'image',
        ]


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['notes', 'status']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Diagnosis / notes (optional)'}),
        }


PrescriptionItemFormSet = inlineformset_factory(
    Prescription,
    PrescriptionItem,
    fields=['medicine', 'dosage', 'frequency', 'duration_days', 'quantity', 'instructions'],
    extra=1,
    can_delete=True,
)
