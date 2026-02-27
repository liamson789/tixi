from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	full_name = models.CharField(max_length=255, blank=True)
	avatar_url = models.URLField(blank=True)
	contact_phone = models.CharField(max_length=30, blank=True)
	auth_provider = models.CharField(max_length=50, default='email')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Profile: {self.user.username}"
