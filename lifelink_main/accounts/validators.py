from django.core.exceptions import ValidationError
import os

def allow_only_images_validator(value):
    _, ext = os.path.splitext(value.name)  # Get the extension
    ext = ext.lower()  # Convert extension to lowercase
    print(ext)
    valid_extensions = ['.png', '.jpeg', '.jpg']
    if not ext in valid_extensions:
        raise ValidationError("Unsupported file extension. Allowed extensions are " + ', '.join(valid_extensions))