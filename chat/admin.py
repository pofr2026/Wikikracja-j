# Third party imports
from django.contrib import admin

# Local folder imports
from .models import Room

admin.site.register(
    Room,
    list_display=["id", "title"],
    list_display_links=["id", "title"],
)
