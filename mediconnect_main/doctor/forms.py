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

