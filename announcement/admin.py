from django.contrib import admin

# Register your models here.
from .models import Announcement, BulkMessage

# Register your models here.
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'applies_to'
    )

@admin.register(BulkMessage)
class BulkMessageAdmin(admin.ModelAdmin):
    list_display = (
        'createdon', 'id', 'title', 'status', 
    )
