from django.contrib.auth.models import AbstractUser
from django.db import models
import random
import string

def generate_verification_code():
    """Generate a random 6-digit code."""
    return ''.join(random.choices(string.digits, k=6))

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)

    def __str__(self):
        return self.username

    def generate_and_set_verification_code(self):
        """Create a new code and save it."""
        self.verification_code = generate_verification_code()
        self.save()
        return self.verification_code
