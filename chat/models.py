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
        return self.allowed.exclude(id=user.id).first()

    # Name that user will see in chats list
    def displayed_name(self, user):
        title_len = 90
        if self.public:
            # Clip public room names to title_len characters for display
            return self.title[:title_len] if len(self.title) > title_len else self.title
        if self.get_other(user) is not None:
            username = self.get_other(user).username
            # Clip long usernames to match room title length
            return username[:title_len] if len(username) > title_len else username
        else:
            return ("--")

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


class MessageVote(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    user = models.ForeignKey(User, related_name="votes", on_delete=models.CASCADE)
    message = models.ForeignKey(Message, related_name="votes", on_delete=models.CASCADE)

    vote_types = [('upvote', 'Upvote'), ('downvote', 'Downvote')]
    vote = models.CharField(choices=vote_types, max_length=50)

    class Meta:
        # can be removed in future to make possible reactions or something like that
        unique_together = ('user', 'message')


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
