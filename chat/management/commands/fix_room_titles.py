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
        
        # Fix Vote rooms
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
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nTotal rooms updated: {task_count + vote_count} '
                f'({task_count} tasks, {vote_count} votes)'
            )
        )
        
        if task_count == 0 and vote_count == 0:
            self.stdout.write(
                self.style.WARNING('No rooms found with Polish prefixes. All rooms are already using English prefixes.')
            )
