"""
Signals for artworks app — automatic slug generation and data integrity.

Kept in a separate file for clean architecture.
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from apps.artworks.models import Artwork, ArtworkTag, Artist, Category


def _generate_unique_slug(model_class, base_slug, instance=None):
    """Generate a unique slug by appending a counter if needed."""
    slug = base_slug
    counter = 1
    queryset = model_class.objects.filter(slug=slug)
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    while queryset.exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
        queryset = model_class.objects.filter(slug=slug)
        if instance and instance.pk:
            queryset = queryset.exclude(pk=instance.pk)
    return slug


@receiver(pre_save, sender=Artist)
def artist_pre_save(sender, instance, **kwargs):
    if not instance.slug:
        base = slugify(instance.artist_name)
        instance.slug = _generate_unique_slug(Artist, base, instance)


@receiver(pre_save, sender=Category)
def category_pre_save(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)


@receiver(pre_save, sender=ArtworkTag)
def tag_pre_save(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)


@receiver(pre_save, sender=Artwork)
def artwork_pre_save(sender, instance, **kwargs):
    if not instance.slug:
        base = slugify(instance.title)
        instance.slug = _generate_unique_slug(Artwork, base, instance)
