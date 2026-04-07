# Standard library imports
import logging
import re

# Third party imports
from django.core.management.base import BaseCommand
from django.db import transaction

# First party imports
from chat.models import Room
from tasks.models import Task

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fix broken connections between tasks and chat rooms by matching room titles with task IDs"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-linking even if task already has a chat room',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        # Statistics
        linked = 0
        already_linked = 0
        missing_rooms = 0
        multiple_rooms = 0
        fixed_broken_links = 0
        
        self.stdout.write("Scanning for broken task-chat room connections...")
        
        # Get all tasks
        tasks = Task.objects.all()
        
        for task in tasks:
            # Skip if already linked and not forcing
            if task.chat_room and not force:
                already_linked += 1
                continue
                
            # Expected room title pattern
            expected_pattern = f"Task #{task.id}:"
            
            # Find rooms that match the pattern for this task ID
            matching_rooms = Room.objects.filter(
                title__startswith=expected_pattern,
                protected=True  # Task rooms are protected
            )
            
            if not matching_rooms.exists():
                missing_rooms += 1
                if not dry_run:
                    self.stdout.write(self.style.WARNING(
                        f"  No room found for task #{task.id}: '{task.title}'"
                    ))
                continue
                
            if matching_rooms.count() > 1:
                multiple_rooms += 1
                self.stdout.write(self.style.ERROR(
                    f"  Multiple rooms found for task #{task.id}: {list(matching_rooms.values_list('title', flat=True))}"
                ))
                continue
                
            room = matching_rooms.first()
            
            # Check if this looks like the correct room
            expected_title = task.get_chat_room_title()
            if room.title != expected_title:
                # Title mismatch - this might be a broken link due to title change
                if dry_run:
                    self.stdout.write(
                        f"  Would fix task #{task.id}: '{room.title}' -> '{expected_title}'"
                    )
                    fixed_broken_links += 1
                else:
                    # Update room title to match current task title
                    with transaction.atomic():
                        room.title = expected_title
                        room.save(update_fields=['title'])
                        task.chat_room = room
                        task.save(update_fields=['chat_room'])
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"  Fixed task #{task.id}: updated room title '{room.title}' -> '{expected_title}'"
                    ))
                    fixed_broken_links += 1
            else:
                # Perfect match, just link
                if dry_run:
                    self.stdout.write(
                        f"  Would link task #{task.id} -> room '{expected_title}'"
                    )
                    linked += 1
                else:
                    with transaction.atomic():
                        task.chat_room = room
                        task.save(update_fields=['chat_room'])
                    
                    self.stdout.write(
                        f"  Linked task #{task.id} -> room '{expected_title}'"
                    )
                    linked += 1
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write("SUMMARY:")
        self.stdout.write(f"  Tasks already linked: {already_linked}")
        self.stdout.write(f"  Tasks newly linked: {linked}")
        self.stdout.write(f"  Broken links fixed: {fixed_broken_links}")
        self.stdout.write(f"  No room found: {missing_rooms}")
        self.stdout.write(f"  Multiple rooms found: {multiple_rooms}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN - No changes made. Use without --dry-run to apply fixes."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nDone! Total tasks processed: {tasks.count()}"))
