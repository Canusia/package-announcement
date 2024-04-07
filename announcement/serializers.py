from django.contrib.auth import get_user_model
from rest_framework import serializers

from cis.serializers.highschool_admin import CustomUserSerializer
from .models.announcement import Announcement, BulkMessage, BulkMessageRecipient, BulkMessageLog


class BulkMessageSerializer(serializers.ModelSerializer):

    ce_url = serializers.CharField(read_only=True)
    sexy_status = serializers.CharField(read_only=True)
    createdon = serializers.DateTimeField(
        format='%Y-%m-%d %I:%M:%S %p'
    )
    send_on_after = serializers.DateTimeField(
        format='%Y-%m-%d %I:%M:%S %p'
    )

    send_until = serializers.DateTimeField(
        format='%Y-%m-%d %I:%M:%S %p'
    )

    createdby = CustomUserSerializer()
    
    class Meta:
        model = BulkMessage
        fields = '__all__'

        datatables_always_serialize = [
            'ce_url',
            'sexy_status',
            'send_on_after'
        ]

class BulkMessageLogSerializer(serializers.ModelSerializer):

    bulk_message = BulkMessageSerializer()

    summary = serializers.CharField(read_only=True)
    command = serializers.CharField(read_only=True)

    # cron = CronTabSerializer()
    
    class Meta:
        model = BulkMessageLog
        fields = '__all__'
        datatables_always_serialize = [
            'summary',
            'bulk_message'
        ]

class BulkMessageRecipientSerializer(serializers.ModelSerializer):

    # ce_url = serializers.CharField(read_only=True)
    
    class Meta:
        model = BulkMessageRecipient
        fields = '__all__'

        datatables_always_serialize = [
            'first_name', 'last_name'
        ]

class AnnouncementSerializer(serializers.ModelSerializer):
    valid_from = serializers.DateField(
        format='%m/%d/%Y',
        input_formats=['%m/%d/%Y']
    )
    valid_until = serializers.DateField(
        format='%m/%d/%Y',
        input_formats=['%m/%d/%Y']
    )
    class Meta:
        model = Announcement
        fields = [
            'id',
            'title',
            'description',
            'applies_to',
            'display_weight',
            'valid_from',
            'valid_until'
        ]
