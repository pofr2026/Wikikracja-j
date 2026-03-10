from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Room(models.Model):
    """
    A room for people to chat in.
    """
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')

    # Allowed users
    allowed = models.ManyToManyField(User, related_name="rooms")

    # For 1to1 chats
    public = models.BooleanField(default=True)

    # For old chats without activity
    archived = models.BooleanField(default=False)
    
    # Room title
    title = models.CharField(max_length=255, unique=True)

    # List of users who saw all messages in this chat
    seen_by = models.ManyToManyField(User, related_name="seen_rooms")

    # List of users who disabled notifications
    muted_by = models.ManyToManyField(User, related_name='muted_rooms')

    # Last activity timestamp
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_other(self, user):
        assert not self.public
        # Use prefetched data if available to avoid extra query
        if hasattr(self, '_prefetched_objects_cache') and 'allowed' in self._prefetched_objects_cache:
            for allowed_user in self.allowed.all():
                if allowed_user.id != user.id:
                    return allowed_user
            return None
        return self.allowed.exclude(id=user.id).first()

    # Name that user will see in chats list
    def displayed_name(self, user):
        title_len = 90
        if self.public:
            # Clip public room names to title_len characters for display
            return self.title[:title_len] if len(self.title) > title_len else self.title
        
        get_user = self.get_other(user)
        if get_user is not None:
            username = get_user.username
            # Clip long usernames to match room title length
            return username[:title_len] if len(username) > title_len else username
        else:
            return "--"

    @property  # adds 'getter', 'setter' and 'deleter' methods
    def group_name(self):
        """
        Returns the Channels Group name that sockets should
        subscribe to to get sent messages as they are generated.
        """
        return "room-%s" % self.id

    @staticmethod
    def find_all_with_users(*users):
        """
        Returns generator of Room objects
        """
        # TODO: replace with better query
        # look through all rooms
        for room in Room.objects.filter(public=False):
            # get all members of the room
            room_members = room.allowed.all()
            # look through users, who must be present in the room
            all_in = True
            for user in users:
                assert isinstance(user, User)
                if user not in room_members:
                    all_in = False
                    break
            if all_in:
                yield room

    @staticmethod
    def find_with_users(*users):
        """
        Returns first matching room.
        """
        for room in Room.find_all_with_users(*users):
            return room

    @staticmethod
    def find_private_rooms_for_user_pairs(user, other_user_ids):
        """
        Optimized: Find all private 1-to-1 rooms between the given user and multiple other users.
        Returns a dictionary mapping other_user_id to Room object.
        This uses a single database query instead of N queries.
        
        Args:
            user: The main user
            other_user_ids: List or queryset of user IDs to find rooms with
            
        Returns:
            dict: {other_user_id: Room} for found rooms
        """
        from django.contrib.auth.models import User
        
        # Convert to list if needed
        other_user_ids = list(other_user_ids)
        
        if not other_user_ids:
            return {}
        
        # Find all private rooms where:
        # 1. public=False
        # 2. user is in allowed
        # 3. room has exactly 2 users (1-to-1)
        # 4. at least one of the other_user_ids is also in allowed
        rooms = Room.objects.filter(
            public=False,
            allowed=user
        ).filter(
            allowed__id__in=other_user_ids
        ).distinct()
        
        # Build mapping: other_user_id -> room
        result = {}
        
        # We need to check each room to find which other user from the pair it corresponds to
        # Since these are 1-to-1 rooms, there should be exactly one other user besides the main user
        for room in rooms:
            # Get the other user in this room (excluding the main user)
            other_users = room.allowed.exclude(id=user.id)
            if other_users.count() == 1:
                other_user = other_users.first()
                if other_user.id in other_user_ids:
                    result[other_user.id] = room
        
        return result


class Message(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    # 'sender' must be 'null=True' for anonymouse messages in email (search for 'if m.anonymous:').
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    time = models.DateTimeField(auto_now=True)
    text = models.TextField()
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    anonymous = models.BooleanField(default=False)
    # TODO: revisions (editMessage(), deleteMessage())

    class Meta:
        unique_together = ('sender', 'text', 'room', 'time')
        indexes = [
            models.Index(fields=['room', 'time'], name='chat_message_room_time_asc_idx'),
        ]


class MessageVote(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    user = models.ForeignKey(User, related_name="votes", on_delete=models.CASCADE)
    message = models.ForeignKey(Message, related_name="votes", on_delete=models.CASCADE)

    vote_types = [('upvote', 'Upvote'), ('downvote', 'Downvote')]
    vote = models.CharField(choices=vote_types, max_length=50)

    class Meta:
        # can be removed in future to make possible reactions or something like that
        unique_together = ('user', 'message')
        indexes = [
            models.Index(fields=['message', 'vote'], name='chat_messagevote_msg_vote_idx'),
        ]


# Store changes history separately,
# so you don't have to deal with it unless you need it
class MessageHistory(models.Model):
    """
    All states of given message will be associated with this object.
    They can be easily retrieved like MessageHistory#entries.
    """
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    message = models.OneToOneField(Message, on_delete=models.CASCADE)


class MessageHistoryEntry(models.Model):
    """ Stores state of message that is no longer relevant """
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    history = models.ForeignKey(MessageHistory, on_delete=models.CASCADE, related_name="entries")
    text = models.TextField()
    time = models.DateTimeField(auto_now=True)


class MessageAttachment(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    type = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")

    class Meta:
        indexes = [
            models.Index(fields=['message'], name='chat_messageattachment_msg_idx'),
        ]
