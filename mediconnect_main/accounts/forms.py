import re

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, UserProfile
from .validators import allow_only_images_validator


NAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z\s'.-]*$")
USERNAME_REGEX = re.compile(r"^[A-Za-z0-9_]+$")
PHONE_REGEX = re.compile(r"^[0-9]{7,12}$")


class LoginForm(forms.Form):
    email = forms.EmailField(
        required=True,
        error_messages={
            'required': 'Email address is required.',
            'invalid': 'Enter a valid email address.',
        },
        widget=forms.EmailInput(attrs={
            'class': 'form-control floating',
            'placeholder': ' ',
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        required=True,
        error_messages={'required': 'Password is required.'},
        widget=forms.PasswordInput(attrs={
            'class': 'form-control floating',
            'placeholder': ' ',
            'autocomplete': 'current-password',
        })
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if user is None:
                existing_user = User.objects.filter(email__iexact=email).first()
                if existing_user and not existing_user.is_active:
                    raise forms.ValidationError('Your account is not activated yet. Please verify your email first.')
                raise forms.ValidationError('Invalid email or password.')
            cleaned_data['user'] = user

        return cleaned_data


class UserForm(forms.ModelForm):
    password = forms.CharField(
        required=True,
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control floating',
            'placeholder': ' ',
            'autocomplete': 'new-password',
        }),
        error_messages={
            'required': 'Password is required.',
            'min_length': 'Password must be at least 8 characters long.',
        }
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control floating',
            'placeholder': ' ',
            'autocomplete': 'new-password',
        }),
        error_messages={'required': 'Please confirm your password.'}
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'phone_number', 'email', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control floating', 'placeholder': ' ', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control floating', 'placeholder': ' ', 'autocomplete': 'family-name'}),
            'username': forms.TextInput(attrs={'class': 'form-control floating', 'placeholder': ' ', 'autocomplete': 'username'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control floating', 'placeholder': ' ', 'autocomplete': 'tel'}),
            'email': forms.EmailInput(attrs={'class': 'form-control floating', 'placeholder': ' ', 'autocomplete': 'email'}),
        }
        error_messages = {
            'first_name': {'required': 'First name is required.'},
            'last_name': {'required': 'Last name is required.'},
            'username': {'required': 'Username is required.'},
            'phone_number': {'required': 'Phone number is required.'},
            'email': {'required': 'Email address is required.', 'invalid': 'Enter a valid email address.'},
        }

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name'].strip()
        if len(first_name) < 2:
            raise forms.ValidationError('First name must contain at least 2 characters.')
        if not NAME_REGEX.match(first_name):
            raise forms.ValidationError('First name can contain letters, spaces, hyphens, apostrophes, and dots only.')
        return first_name.title()

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name'].strip()
        if len(last_name) < 2:
            raise forms.ValidationError('Last name must contain at least 2 characters.')
        if not NAME_REGEX.match(last_name):
            raise forms.ValidationError('Last name can contain letters, spaces, hyphens, apostrophes, and dots only.')
        return last_name.title()

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if len(username) < 4:
            raise forms.ValidationError('Username must be at least 4 characters long.')
        if not USERNAME_REGEX.match(username):
            raise forms.ValidationError('Username can contain letters, numbers, and underscores only.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number'].strip().replace(' ', '').replace('-', '')
        if not PHONE_REGEX.match(phone_number):
            raise forms.ValidationError('Enter a valid phone number with 7 to 12 digits only.')
        return phone_number

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')

        if password:
            errors = []
            if not re.search(r'[A-Z]', password):
                errors.append('one uppercase letter')
            if not re.search(r'[a-z]', password):
                errors.append('one lowercase letter')
            if not re.search(r'[0-9]', password):
                errors.append('one number')
            if not re.search(r'[^A-Za-z0-9]', password):
                errors.append('one special character')

            if errors:
                raise forms.ValidationError('Password must contain at least ' + ', '.join(errors) + '.')

            try:
                validate_password(password)
            except ValidationError as exc:
                raise forms.ValidationError(exc.messages)

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')

        return cleaned_data


class UserProfileForm(forms.ModelForm):
    address = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your full address',
            'class': 'form-control',
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
            'address': forms.TextInput(attrs={
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
