from django.core.management.base import BaseCommand
from chat.models import Room
import logging

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix room titles to use English prefixes for proper categorization'

    def handle(self, *args, **options):
        """
        Update room titles from Polish prefixes to English prefixes:
        - "Zadanie #" -> "Task #"
        - "Głosowanie #" -> "Vote #"
        - "#ID:Title" -> "Vote #ID: Title" (old format voting rooms)
        """
        
        # Fix Task rooms
        task_rooms = Room.objects.filter(title__startswith="Zadanie #")
        task_count = 0
        for room in task_rooms:
            old_title = room.title
            new_title = room.title.replace("Zadanie #", "Task #", 1)
            room.title = new_title
            room.save()
            task_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Updated: "{old_title}" -> "{new_title}"')
            )
        
        # Fix Vote rooms with Polish prefix
        vote_rooms = Room.objects.filter(title__startswith="Głosowanie #")
        vote_count = 0
        for room in vote_rooms:
            old_title = room.title
            new_title = room.title.replace("Głosowanie #", "Vote #", 1)
            room.title = new_title
            room.save()
            vote_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Updated: "{old_title}" -> "{new_title}"')
            )
        
        # Fix old format voting rooms (#ID:Title -> Vote #ID: Title)
        import re
        old_format_rooms = Room.objects.filter(title__regex=r'^#\d+:')
        old_format_count = 0
        for room in old_format_rooms:
            old_title = room.title
            # Replace #ID: with Vote #ID: 
            new_title = re.sub(r'^#(\d+):', r'Vote #\1: ', room.title)
            room.title = new_title
            room.save()
            old_format_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Updated: "{old_title}" -> "{new_title}"')
            )
        
        total_count = task_count + vote_count + old_format_count
        self.stdout.write(
            self.style.SUCCESS(
                f'\nTotal rooms updated: {total_count} '
                f'({task_count} tasks, {vote_count + old_format_count} votes)'
            )
        )
        
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('No rooms found to update. All rooms are already using correct prefixes.')
            )
