import logging
from django.core.management.base import BaseCommand
from chat.models import Room
from django.contrib.auth.models import User

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix room permissions by adding users to allowed list based on room title'

    def handle(self, *args, **options):
        fixed_count = 0
        
        # Fix private rooms
        private_rooms = Room.objects.filter(public=False)
        for room in private_rooms:
            # Parse usernames from room title (format: "user1-user2")
            usernames = room.title.split('-')
            if len(usernames) != 2:
                log.warning(f"Room {room.id} has invalid title format: {room.title}")
                continue
            
            # Get users
            users = []
            for username in usernames:
                try:
                    user = User.objects.get(username=username)
                    users.append(user)
                except User.DoesNotExist:
                    log.warning(f"User {username} not found for room {room.id}")
            
            if len(users) == 2:
                # Check if allowed list is empty or incorrect
                current_allowed = set(room.allowed.all())
                expected_allowed = set(users)
                
                if current_allowed != expected_allowed:
                    room.allowed.set(users)
                    fixed_count += 1
                    log.info(f"Fixed room {room.id} ({room.title})")
        
        # Fix public rooms - add all active users
        public_rooms = Room.objects.filter(public=True)
        active_users = list(User.objects.filter(is_active=True))
        
        self.stdout.write(f"Active users: {[u.id for u in active_users]}")
        
        for room in public_rooms:
            current_allowed = list(room.allowed.all())
            current_allowed_ids = [u.id for u in current_allowed]
            expected_allowed_ids = [u.id for u in active_users]
            
            self.stdout.write(f"Room {room.id} ({room.title}):")
            self.stdout.write(f"  Current: {current_allowed_ids}")
            self.stdout.write(f"  Expected: {expected_allowed_ids}")
            
            if set(current_allowed) != set(active_users):
                room.allowed.set(active_users)
                fixed_count += 1
                self.stdout.write(self.style.SUCCESS(f"  -> FIXED"))
            else:
                self.stdout.write(f"  -> OK")
        
        self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} rooms'))
