# Generated by Django 3.2 on 2023-07-12 14:35

import ckeditor.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('announcement', '0010_auto_20201221_1218'),
    ]

    operations = [
        migrations.AlterField(
            model_name='announcement',
            name='description',
            field=ckeditor.fields.RichTextField(),
        ),
    ]
