from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'auth_provider', 'full_name', 'updated_at')
	search_fields = ('user__username', 'user__email', 'full_name')
