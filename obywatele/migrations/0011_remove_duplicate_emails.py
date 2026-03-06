from django.db import migrations
from django.contrib.auth.models import User
from django.db.models import Count


def remove_duplicate_emails(apps, schema_editor):
    """
    Remove duplicate users with the same email address.
    Keeps the active user and removes/deactivates inactive duplicates.
    """
    # Find emails that appear more than once
    duplicate_emails = User.objects.values('email').annotate(
        count=Count('id')
    ).filter(count__gt=1, email__isnull=False).exclude(email='')
    
    for dup in duplicate_emails:
        email = dup['email']
        users = User.objects.filter(email__iexact=email).order_by('is_active', '-date_joined')
        
        # Keep the first user (prefer active users, then most recent)
        users_to_delete = users[1:]
        
        for user in users_to_delete:
            try:
                user.delete()
            except Exception as e:
                print(f"Error deleting user {user.id} with email {email}: {e}")


def reverse_remove_duplicate_emails(apps, schema_editor):
    # This migration cannot be reversed as we're deleting data
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('obywatele', '0010_uzytkownik_onboarding_status'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_emails, reverse_remove_duplicate_emails),
    ]
