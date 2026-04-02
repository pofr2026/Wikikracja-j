# Third party imports
from django.contrib import admin

# Local folder imports
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'place', 'frequency', 'is_active', 'created_at']
    list_filter = ['frequency', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'place']
    date_hierarchy = 'start_date'
    ordering = ['start_date']

    fieldsets = (
        (None, {
            'fields': ('title', 'description')
        }),
        ('Location & Link', {
            'fields': ('place', 'link')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'frequency', 'monthly_ordinal', 'monthly_weekday'),
            'description': 'For monthly ordinal frequency, specify which week of the month and which day of the week.'
        }),
        ('Status', {
            'fields': ('is_active', 'is_public')
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('created_at', 'updated_at')
        return self.readonly_fields
