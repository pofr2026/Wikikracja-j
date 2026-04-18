# Third party imports
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class FeedItem(models.Model):
    """A unified feed item that can represent any activity in the system"""
    
    class ContentType(models.TextChoices):
        POST = 'post', _('Post')
        TASK = 'task', _('Task')
        BOOK = 'book', _('Book')
        EVENT = 'event', _('Event')
        MESSAGE = 'message', _('Message')
        DECISION = 'decision', _('Decision')
        CITIZEN = 'citizen', _('Citizen Activity')
    
    content_type = models.CharField(max_length=20, choices=ContentType.choices)
    object_id = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField()
    url = models.CharField(max_length=500)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp'], name='feed_item_timestamp_idx'),
            models.Index(fields=['content_type', 'object_id'], name='feed_item_content_idx'),
        ]
    
    def __str__(self):
        return f"{self.content_type}: {self.title}"


class ReadStatus(models.Model):
    """Track which users have read which content"""
    
    class ContentType(models.TextChoices):
        POST = 'post', _('Post')
        TASK = 'task', _('Task')
        BOOK = 'book', _('Book')
        EVENT = 'event', _('Event')
        MESSAGE = 'message', _('Message')
        DECISION = 'decision', _('Decision')
        CITIZEN = 'citizen', _('Citizen Activity')
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.CharField(max_length=20, choices=ContentType.choices)
    object_id = models.PositiveIntegerField()
    read_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'content_type', 'object_id']
        indexes = [
            models.Index(fields=['user', 'content_type'], name='readstatus_user_content_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.username} read {self.content_type} #{self.object_id}"


class OnboardingProgress(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='onboarding')
    docs_read = models.ManyToManyField('board.Post', blank=True, related_name='+')
    step_argued = models.BooleanField(default=False)
    step_chatted = models.BooleanField(default=False)
    step_voted = models.BooleanField(default=False)

    def is_completed(self, required_posts):
        if required_posts:
            read_ids = set(self.docs_read.values_list('id', flat=True))
            if not all(p.id in read_ids for p in required_posts):
                return False
        return self.step_argued and self.step_chatted and self.step_voted

    @property
    def completed(self):
        from site_settings.models import SiteSettings
        ss = SiteSettings.get()
        required = list(ss.onboarding_posts.all())
        return self.is_completed(required)
