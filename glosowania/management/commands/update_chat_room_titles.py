from django.core.management.base import BaseCommand
from glosowania.models import Decyzja


class Command(BaseCommand):
    # TODO: Wszystkie pokoje zostały już zaktualizowane, nowe pokoje będą miały już poprawne tytuły. Można usunąć cały ten skrypt.
    help = 'Update existing chat room titles to include voting numbers'

    def handle(self, *args, **options):
        """Update all existing chat room titles to include voting numbers."""
        
        decyzje_with_rooms = Decyzja.objects.filter(chat_room__isnull=False)
        
        self.stdout.write(f"Found {decyzje_with_rooms.count()} voting projects with chat rooms")
        
        updated_count = 0
        
        for decyzja in decyzje_with_rooms:
            old_title = decyzja.chat_room.title
            new_title = decyzja.get_chat_room_title()
            
            if old_title != new_title:
                decyzja.chat_room.title = new_title
                decyzja.chat_room.save(update_fields=['title'])
                self.stdout.write(f"Updated: '{old_title}' -> '{new_title}'")
                updated_count += 1
            else:
                self.stdout.write(f"No change needed for: '{old_title}'")
        
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_count} chat room titles"))
