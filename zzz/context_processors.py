from django.http import HttpRequest
from board.models import Post
import logging

log = logging.getLogger(__name__)

def footer(request: HttpRequest):
    footer = Post.objects.filter(title__iexact='Footer').order_by('-updated').first()
        
    return {'footer': footer}
