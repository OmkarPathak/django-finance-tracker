from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Category, UserProfile
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile for every new user."""
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure UserProfile is saved when User is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def create_default_categories(sender, instance, created, **kwargs):
    if created:
        default_categories = ['Food', 'Travel', 'Shopping', 'Bills', 'Entertainment', 'Others']
        for category_name in default_categories:
            Category.objects.get_or_create(user=instance, name=category_name)

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """Send welcome email to new users (skip demo user)."""
    if created and instance.email and instance.username != 'demo':
        try:
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            from django.conf import settings

            html_message = render_to_string('email/welcome_email.html', {
                'user': instance,
            })

            send_mail(
                subject='Welcome to TrackMyRupee! 🎉',
                message='Welcome to TrackMyRupee! Start tracking your finances today.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                html_message=html_message,
            )
            logger.info(f"Welcome email sent to {instance.email}")
        except Exception as e:
            # Never block signup if email fails
            logger.error(f"Failed to send welcome email to {instance.email}: {e}")

