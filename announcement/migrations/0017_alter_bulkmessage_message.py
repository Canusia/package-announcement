# Generated by Django 4.2 on 2024-04-04 01:25

from django.db import migrations
import django_ckeditor_5.fields


class Migration(migrations.Migration):

    dependencies = [
        ('announcement', '0016_bulkmessage_cron_bulkmessage_send_until_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bulkmessage',
            name='message',
            field=django_ckeditor_5.fields.CKEditor5Field(blank=True, verbose_name='Text'),
        ),
    ]