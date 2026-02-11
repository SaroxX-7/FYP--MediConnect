from django.db import models
from accounts.models import User, UserProfile

# Create your models here.
class Patient(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    def __str__(self):
        return self.user.email
