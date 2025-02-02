# Generated by Django 4.2 on 2024-04-04 16:01

import announcement.models.announcement
import cis.storage_backend
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('announcement', '0017_alter_bulkmessage_message'),
    ]

    operations = [
        migrations.CreateModel(
            name='BulkMessageLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('run_completed_on', models.DateTimeField(blank=True, null=True)),
                ('run_started_on', models.DateTimeField(blank=True, null=True)),
                ('run_scheduled_for', models.DateTimeField(blank=True, null=True)),
                ('meta', models.JSONField(default=dict)),
                ('log_file', models.FileField(blank=True, storage=cis.storage_backend.PrivateMediaStorage(), upload_to=announcement.models.announcement.bulk_message_log_upload_path)),
                ('bulk_message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='announcement.bulkmessage')),
            ],
        ),
    ]
