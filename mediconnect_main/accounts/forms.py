from django import forms
from .models import User, UserProfile
from .validators import allow_only_images_validator



class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'phone_number', 'email', 'password']

    def clean(self):
        cleaned_data = super(UserForm, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError(
                "Password does not match!"
            )
# attrs={'placeholder': 'Start typing...', 'required': 'required'}

class UserProfileForm(forms.ModelForm):
    address = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your full address',
            'class': 'form-control',  # Explicitly add form-control class
            'id': 'my_address_field'
        }),
        required=False
    )
    profile_picture = forms.FileField(widget=forms.FileInput(attrs={'class': 'btn btn-info'}),
                                      validators=[allow_only_images_validator])


    
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'date_of_birth', 'gender', 'blood_group', 'address', 'country', 'state', 'city', 'pin_code',]
        widgets = {
            'address': forms.TextInput(attrs={  # Define again in Meta
                'class': 'form-control',
                'placeholder': 'Enter your full address',
                'id': 'my_address_field'
            }),
           
        }
                  

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)

class UserInfoForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'email', 'username']


