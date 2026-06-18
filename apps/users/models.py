from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    """Custom user model."""

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email or self.username


class Profile(models.Model):
    """Extended profile linked one-to-one with User."""

    class AccountType(models.TextChoices):
        COLLECTOR = "collector", "Collector"
        ARTIST = "artist", "Artist"
        DEALER = "dealer", "Dealer"
        CURATOR = "curator", "Curator"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_picture = models.ImageField(
        upload_to="profile_pics/", blank=True, default="profile_pics/default.svg"
    )
    bio = models.TextField(max_length=500, blank=True)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.COLLECTOR
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """Auto-create a Profile whenever a new User is registered."""
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()
