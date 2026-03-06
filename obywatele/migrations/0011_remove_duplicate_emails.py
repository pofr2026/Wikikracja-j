from django.db import migrations
from django.contrib.auth.models import User
from django.db.models import Count


def remove_duplicate_emails(apps, schema_editor):
    """
    Remove duplicate users with the same email address.
    Keeps the active user and removes/deactivates inactive duplicates.
    Also removes orphaned Uzytkownik records that don't have a corresponding User.
    """
    Uzytkownik = apps.get_model('obywatele', 'Uzytkownik')
    
    # Get all models that might have foreign keys to auth_user
    models_to_check = {}
    for model_name in ['MessageVote', 'Message', 'Room', 'Post', 'Book', 'Decyzja', 'Argument', 'ZebranePodpisy']:
        try:
            app_name = 'chat' if model_name in ['MessageVote', 'Message', 'Room'] else \
                      'board' if model_name == 'Post' else \
                      'elibrary' if model_name == 'Book' else \
                      'glosowania'
            models_to_check[model_name] = apps.get_model(app_name, model_name)
        except LookupError:
            pass
    
    try:
        Rate = apps.get_model('obywatele', 'Rate')
    except LookupError:
        Rate = None
    
    # First, remove orphaned Uzytkownik records (where uid_id doesn't exist in auth_user)
    orphaned = Uzytkownik.objects.filter(uid_id__isnull=True)
    orphaned_count = orphaned.count()
    orphaned.delete()
    print(f"Deleted {orphaned_count} orphaned Uzytkownik records with null uid_id")
    
    # Also remove Uzytkownik records where the referenced User doesn't exist
    all_uzytkownik = Uzytkownik.objects.all()
    for uz in all_uzytkownik:
        if not User.objects.filter(id=uz.uid_id).exists():
            print(f"Deleting orphaned Uzytkownik id={uz.id} with non-existent uid_id={uz.uid_id}")
            uz.delete()
    
    # Clean up orphaned foreign key references in all models that reference User
    valid_user_ids = set(User.objects.values_list('id', flat=True))
    
    # Clean up ManyToMany tables for Room model
    if 'Room' in models_to_check:
        Room = models_to_check['Room']
        # Clean up room_allowed (ManyToMany)
        for room in Room.objects.all():
            invalid_users = room.allowed.exclude(id__in=valid_user_ids)
            if invalid_users.exists():
                room.allowed.remove(*invalid_users)
                print(f"Removed {invalid_users.count()} orphaned users from Room {room.id} allowed list")
            
            # Clean up seen_by (ManyToMany)
            invalid_seen = room.seen_by.exclude(id__in=valid_user_ids)
            if invalid_seen.exists():
                room.seen_by.remove(*invalid_seen)
                print(f"Removed {invalid_seen.count()} orphaned users from Room {room.id} seen_by list")
            
            # Clean up muted_by (ManyToMany)
            invalid_muted = room.muted_by.exclude(id__in=valid_user_ids)
            if invalid_muted.exists():
                room.muted_by.remove(*invalid_muted)
                print(f"Removed {invalid_muted.count()} orphaned users from Room {room.id} muted_by list")
    
    # MessageVote.user
    if 'MessageVote' in models_to_check:
        orphaned_votes = models_to_check['MessageVote'].objects.exclude(user_id__in=valid_user_ids)
        orphaned_votes_count = orphaned_votes.count()
        orphaned_votes.delete()
        print(f"Deleted {orphaned_votes_count} orphaned MessageVote records")
    
    # Message.sender
    if 'Message' in models_to_check:
        orphaned_messages = models_to_check['Message'].objects.filter(sender_id__isnull=False).exclude(sender_id__in=valid_user_ids)
        orphaned_messages_count = orphaned_messages.count()
        orphaned_messages.delete()
        print(f"Deleted {orphaned_messages_count} orphaned Message records")
    
    # Post.author
    if 'Post' in models_to_check:
        orphaned_posts = models_to_check['Post'].objects.filter(author_id__isnull=False).exclude(author_id__in=valid_user_ids)
        orphaned_posts_count = orphaned_posts.count()
        orphaned_posts.delete()
        print(f"Deleted {orphaned_posts_count} orphaned Post records")
    
    # Book.uploader
    if 'Book' in models_to_check:
        orphaned_books = models_to_check['Book'].objects.filter(uploader_id__isnull=False).exclude(uploader_id__in=valid_user_ids)
        orphaned_books_count = orphaned_books.count()
        orphaned_books.delete()
        print(f"Deleted {orphaned_books_count} orphaned Book records")
    
    # Decyzja.author
    if 'Decyzja' in models_to_check:
        orphaned_decyzja = models_to_check['Decyzja'].objects.filter(author_id__isnull=False).exclude(author_id__in=valid_user_ids)
        orphaned_decyzja_count = orphaned_decyzja.count()
        orphaned_decyzja.delete()
        print(f"Deleted {orphaned_decyzja_count} orphaned Decyzja records")
    
    # Argument.author
    if 'Argument' in models_to_check:
        orphaned_arguments = models_to_check['Argument'].objects.filter(author_id__isnull=False).exclude(author_id__in=valid_user_ids)
        orphaned_arguments_count = orphaned_arguments.count()
        orphaned_arguments.delete()
        print(f"Deleted {orphaned_arguments_count} orphaned Argument records")
    
    # ZebranePodpisy.podpis_uzytkownika
    if 'ZebranePodpisy' in models_to_check:
        orphaned_podpisy = models_to_check['ZebranePodpisy'].objects.filter(podpis_uzytkownika_id__isnull=False).exclude(podpis_uzytkownika_id__in=valid_user_ids)
        orphaned_podpisy_count = orphaned_podpisy.count()
        orphaned_podpisy.delete()
        print(f"Deleted {orphaned_podpisy_count} orphaned ZebranePodpisy records")
    
    # Clean up orphaned foreign key references in Rate table
    if Rate:
        valid_uzytkownik_ids = set(Uzytkownik.objects.values_list('id', flat=True))
        orphaned_rates = Rate.objects.exclude(kandydat_id__in=valid_uzytkownik_ids)
        orphaned_rates.delete()
        orphaned_rates = Rate.objects.exclude(obywatel_id__in=valid_uzytkownik_ids)
        orphaned_rates.delete()
        print(f"Deleted orphaned Rate records with non-existent Uzytkownik references")
    
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
                print(f"Deleting duplicate user id={user.id} with email {email}")
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
