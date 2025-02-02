# Generated by Django 2.2.5 on 2019-10-28 15:50

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('announcement', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('applies_to', models.CharField(choices=[('Students', 'Students'), ('High School Administrators', 'High School Administrators')], max_length=30)),
                ('display_weight', models.SmallIntegerField(default=0)),
                ('valid_from', models.DateField()),
                ('valid_until', models.DateField()),
            ],
            options={
                'unique_together': {('title', 'applies_to')},
            },
        ),
    ]
