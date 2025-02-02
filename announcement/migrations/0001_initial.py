# Generated by Django 2.2.5 on 2019-10-16 17:43

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ImportantLink',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('link', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('applies_to', models.CharField(choices=[('Students', 'Students'), ('High School Administrators', 'High School Administrators')], max_length=30)),
                ('display_weight', models.SmallIntegerField(default=0)),
                ('status', models.CharField(choices=[('Active', 'Active'), ('Inactive', 'Inactive')], default='Active', max_length=30)),
            ],
            options={
                'unique_together': {('link', 'applies_to')},
            },
        ),
    ]
