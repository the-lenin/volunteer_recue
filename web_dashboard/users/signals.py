from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def add_default_group_if_none(sender, instance, **kwargs):
    if kwargs.get('created', False) and not instance.groups.exists():
        default_group_name = 'Volunteer'
        default_group, __ = Group.objects.get_or_create(
            name=default_group_name
        )
        instance.groups.add(default_group)
