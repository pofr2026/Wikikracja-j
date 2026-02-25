from django.http import HttpRequest
from board.models import Post
import logging

logging.basicConfig(filename='/var/log/wiki.log', datefmt='%d-%b-%y %H:%M:%S', format='%(asctime)s %(levelname)s %(funcName)s() %(message)s', level=logging.INFO)

def footer(request: HttpRequest):
    try:
        footer = Post.objects.get(title='Footer')
    except Exception as e: # type: ignore
        footer = ''
        
    return {'footer': footer}
