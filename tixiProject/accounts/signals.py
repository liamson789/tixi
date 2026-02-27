from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import UserProfile


def _google_profile_data(user):
    try:
        from allauth.socialaccount.models import SocialAccount
    except Exception:
        return None

    account = SocialAccount.objects.filter(user=user, provider='google').first()
    if not account:
        return None

    extra_data = account.extra_data or {}
    full_name = extra_data.get('name')
    if not full_name:
        given_name = extra_data.get('given_name', '')
        family_name = extra_data.get('family_name', '')
        full_name = f"{given_name} {family_name}".strip()

    return {
        'full_name': full_name or '',
        'avatar_url': extra_data.get('picture', '') or '',
        'auth_provider': 'google',
    }


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(user_logged_in)
def sync_profile_on_login(sender, request, user, **kwargs):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    google_data = _google_profile_data(user)
    if not google_data:
        if not profile.auth_provider:
            profile.auth_provider = 'email'
            profile.save(update_fields=['auth_provider'])
        return

    fields_to_update = []
    for field_name, value in google_data.items():
        if getattr(profile, field_name) != value:
            setattr(profile, field_name, value)
            fields_to_update.append(field_name)

    if fields_to_update:
        profile.save(update_fields=fields_to_update + ['updated_at'])


@receiver(post_migrate)
def backfill_profiles(sender, **kwargs):
    if sender.name != 'accounts':
        return

    for user in User.objects.all().iterator():
        UserProfile.objects.get_or_create(user=user)
