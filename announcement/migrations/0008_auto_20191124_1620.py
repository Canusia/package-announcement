# Generated by Django 2.2.7 on 2019-11-24 22:20

from django.db import migrations
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('announcement', '0007_auto_20191123_1427'),
    ]

    operations = [
        migrations.AlterField(
            model_name='announcement',
            name='description',
            field=tinymce.models.HTMLField(),
        ),
    ]
