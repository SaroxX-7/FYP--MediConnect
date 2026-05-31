from django import forms
from .models import Doctor


from django import forms
from .models import Doctor, Education, Experience, Award, Membership, Registration

class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['doctor_license', 'biography', 'clinic_name', 'clinic_address',
                  'contact_phone', 'contact_email', 'clinic_latitude', 'clinic_longitude', 'department']
        widgets = {
            'biography': forms.Textarea(attrs={'rows': 5}),
        }

class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ['degree', 'institution', 'graduation_year']

class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = ['hospital_name', 'from_date', 'to_date', 'designation']

class AwardForm(forms.ModelForm):
    class Meta:
        model = Award
        fields = ['name', 'year']

class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ['name']

class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ['registration_number', 'year']


from django import forms
from doctor.models import DoctorBilling


class DoctorBillingForm(forms.ModelForm):
    class Meta:
        model = DoctorBilling
        fields = ['consultation_fee', 'esewa_number', 'esewa_enabled']
        widgets = {
            'consultation_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Charge per 30 mins'
            }),
            'esewa_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter eSewa ID / number'
            }),
            'esewa_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'consultation_fee': 'Charge per 30 mins',
            'esewa_number': 'eSewa ID / Number',
            'esewa_enabled': 'Enable eSewa Payment',
        }
