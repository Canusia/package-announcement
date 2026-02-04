"""
    Important Link CE URL Configuration
"""
from django.urls import path, include
from rest_framework import routers

from ..views.views import (
    index, detail, add_new, delete,
    bulk_message_logs,
    bulk_messages,
    bulk_message,
    bulk_message_preview,
    bulk_message_delete_all_recipients,
    bulk_message_add_new,
    bulk_message_delete,
    AnnouncementViewSet,
    BulkMessageViewSet, BulkMessageRecipientViewSet,
    BulkMessageLogViewSet,
    bulk_message_get_datasource_filters,

    track_email
)

app_name = 'announcements'

router = routers.DefaultRouter()
router.register('announcements', AnnouncementViewSet, basename='announcements')
router.register('bulk_messages', BulkMessageViewSet, basename='bulk_messages')
router.register('bulk_message_logs', BulkMessageLogViewSet, basename='bulk_message_logs')
router.register('bulk_messages_recipients', BulkMessageRecipientViewSet, basename='bulk_messages_recipients')

urlpatterns = [
    path('', index, name='all'),
    path('announcement/<uuid:record_id>', detail, name='announcement'),
    path('announcement/add_new', add_new, name='add_new'),
    path('announcement/delete/<uuid:record_id>', delete, name='delete'),

    path('bulk_message_logs', bulk_message_logs, name='bulk_message_logs'),

    path('bulk_messages', bulk_messages, name='bulk_messages'),
    path('bulk_message/add_new', bulk_message_add_new, name='bulk_message_add_new'),
    path('bulk_message/get_datasource_filters', bulk_message_get_datasource_filters, name='get_datasource_filters'),
    path('bulk_message/<uuid:record_id>', bulk_message, name='bulk_message'),
    path('bulk_message/preview/<uuid:record_id>', bulk_message_preview, name='bulk_message_preview'),
    path('bulk_message/delete/<uuid:record_id>', bulk_message_delete, name='bulk_message_delete'),
    path('bulk_message/delete_all_recipients/<uuid:record_id>', bulk_message_delete_all_recipients, name='bulk_message_delete_all_recipients'),

    path('api/', include(router.urls)),

    path('bulk_mailer/tracker/', track_email, name='track_bulk_mail'),
]
