# users/models.py
import os, uuid, datetime, csv, io, logging
from django.conf import settings

from django.contrib.auth import get_user_model
from django.db import models, IntegrityError
from django.dispatch import receiver
from multiselectfield import MultiSelectField
from django.urls import reverse_lazy
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe

from django.template.loader import get_template, render_to_string
from django.template import Context, Template
from django.shortcuts import render, get_object_or_404

from django.db.models import JSONField

from mailer import send_mail, send_html_mail

from cis.storage_backend import PrivateMediaStorage

from django_ckeditor_5.fields import CKEditor5Field as RichTextField
from cis.utils import get_uploaded_file, bulk_message_log_upload_path, bulk_message_media_upload_path

logger = logging.getLogger(__name__)


from django.utils.functional import lazy
def applies_to_choices():
    myce_settings = getattr(settings, 'MY_CE')

    roles = myce_settings.get('roles')
    result = []
    for role_id, role in roles.items():
        result.append(
            (role_id, role['nice_name'])
        )
    return result
    
class Announcement(models.Model):
    """
    model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    # description = models.TextField()
    description = RichTextField('Text')

    STUDENTS = 'Students'
    SCHOOL_ADMINS = 'High School Administrators'

    APPLIES_TO = [
        (STUDENTS, STUDENTS),
        (SCHOOL_ADMINS, SCHOOL_ADMINS),
        ('Instructors', 'Instructors'),
        ('Faculty', 'Faculty'),
    ]


    applies_to = MultiSelectField(
        max_length=300,
        choices=lazy(applies_to_choices, list)()
    )

    display_weight = models.SmallIntegerField(default=0)
    valid_from = models.DateField()
    valid_until = models.DateField()

    def __str__(self):
        return self.title

class BulkMessageRecipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    bulk_message = models.ForeignKey('announcement.BulkMessage', on_delete=models.PROTECT)

    email = models.EmailField(blank=False)
    first_name = models.CharField(max_length=128, blank=True, null=True)
    last_name = models.CharField(max_length=128, blank=True, null=True)
        
    meta = models.JSONField(default=dict)

    STATUS_OPTIONS = [
        ('', ''),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('sent', 'Sent'),
    ]

    status = models.CharField(
        max_length=30,
        choices=STATUS_OPTIONS,
        default='',
        blank=True,
        null=True
    )

class BulkMessage(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)

    message = RichTextField('Text', blank=True)

    send_summary = models.JSONField(default=dict)
    datasource = models.JSONField(default=dict)
    
    meta = models.JSONField(default=dict)

    media = models.FileField(
        storage=PrivateMediaStorage(),
        upload_to=bulk_message_media_upload_path,
        blank=True,
        null=True
    )

    createdon = models.DateTimeField(auto_now_add=True)
    createdby = models.ForeignKey('cis.CustomUser', on_delete=models.PROTECT)
    
    send_on_after = models.DateTimeField(blank=True, null=True)
    send_until = models.DateTimeField(blank=True, null=True)
    
    cron = models.CharField(max_length=100)
    
    STATUS_OPTIONS = [
        ('draft', 'Draft'),
        ('ready_to_send', 'Ready to Send'),
        ('sent', 'Sent'),
    ]

    status = models.CharField(
        max_length=30,
        choices=STATUS_OPTIONS,
        default='draft',
        blank=True,
        null=True
    )

    def delete_me(self):
        self.bulkmessagerecipient_set.all().delete()

        self.delete()
        return True

    @property
    def sexy_status(self):
        for k, v in self.STATUS_OPTIONS:
            if k == self.status:
                return v
        return '-'

    @property
    def can_edit(self):
        if self.status == 'sent':
            return False
        return True

    def format_cols(self, columns):
        result = {}
        
        for col in columns:
            org = col[:]
            col = col.strip().replace(' ', '_').lower()
            result[org] = col

        return result

    def has_recipients(self):
        if self.is_from_datasource():
            return True

        if self.bulkmessagerecipient_set.all().count() > 0:
            return True
        return False

    def should_message_be_sent(self):
        if self.status != 'ready_to_send':
            return False

        # Check if today is one of the selected send dates
        send_dates_str = self.meta.get('send_dates', '')
        if not send_dates_str:
            return False

        today = datetime.date.today()
        send_dates = [d.strip() for d in send_dates_str.split(',') if d.strip()]

        date_match = False
        for d in send_dates:
            try:
                parsed = datetime.datetime.strptime(d, '%m/%d/%Y').date()
                if parsed == today:
                    date_match = True
                    break
            except ValueError:
                continue

        if not date_match:
            return False

        # Check if current time is within the send window
        send_time_str = self.meta.get('send_time', '')
        if not send_time_str:
            return False

        try:
            send_time = datetime.datetime.strptime(send_time_str, '%I:%M %p').time()
        except ValueError:
            return False

        now = datetime.datetime.now()
        cron_interval = getattr(settings, 'MYCE_CRON_INTERVAL', 60)
        window_start = now - datetime.timedelta(minutes=cron_interval)

        send_dt = datetime.datetime.combine(today, send_time)
        return window_start <= send_dt <= now

    def tracking_url(self, recipient_id):
        from cis.utils import getDomain
        url = getDomain() + reverse_lazy('announcements:track_bulk_mail') + f"?bulk_message_id={self.id}&recipient={recipient_id}&date=" + datetime.datetime.now().strftime('%Y-%m-%d')

        img = f'<img src="{url}" width="1" height="1" style="display:none;" alt=""/>'
        return img
    
    def mark_as_opened(self, request):
        recipient_id = request.GET.get('recipient')
        
        datasource_name = self.datasource['name']
        datasource = BulkMessage.get_datasource_object(datasource_name)

        try:
            datasource.mark_as_opened(
                recipient_id,
                self
            )
        except Exception as e:
            print(e)
            
    def send(self):
        short_codes = self.short_codes
        email = self.message

        email_template = Template(email)

        summary = ''
        detailed_log = {
            'success': [],
            'fail': []
        }
        
        datasource_name = self.datasource['name']
        datasource = BulkMessage.get_datasource_object(datasource_name)


        recipients = self.recipients()

        summary += '<br>Starting to send on - ' + str(datetime.datetime.now())
        summary += '<br>Total Receipients - ' + str(len(recipients))

        if self.is_from_datasource():
            for row in recipients:
                context = Context(row)
                text_body = email_template.render(context)

                template = get_template('cis/email.html')
                html_body = template.render({
                    'message': text_body
                })

                html_body += self.tracking_url(row.get('recipient_id'))

                to = row['email']
                if type(to) != list:
                    to = []
                    to.append(row['email'])
                
                for t in to:
                    detailed_log['success'].append({
                        t: text_body
                    })

                send_html_mail(
                    self.subject(),
                    text_body,
                    html_body,
                    settings.DEFAULT_FROM_EMAIL,
                    to
                )

                try:
                    # tell the datasource that the message has been sent
                    datasource.post_send(
                        row,
                        self
                    )
                except Exception as e:
                    print(e)
                # break
        else:
            short_codes = self.short_codes

            for row in recipients:
                recp = row.meta
                formatted_row = {}

                for k, v in recp.items():
                    formatted_row[
                        short_codes.get(k)
                    ] = v

                context = Context(formatted_row)
                text_body = email_template.render(context)

                template = get_template('cis/email.html')
                html_body = template.render({
                    'message': text_body
                })

                to = row.email
                if type(to) != list:
                    to = list()
                    to.append(row.email)
                
                for t in to:
                    detailed_log['success'].append({
                        t: text_body
                    })

                send_html_mail(
                    self.subject(),
                    text_body,
                    html_body,
                    settings.DEFAULT_FROM_EMAIL,
                    to
                )

        summary += '<br>Ended send on - ' + str(datetime.datetime.now())
        return (summary, detailed_log)

        
    def preview(self):

        short_codes = self.short_codes
        email = self.message

        email_template = Template(email)
        sample_row = self.sample_row()

        formatted_row = {}
        if self.is_from_datasource():
            formatted_row = sample_row
        else:
            for k, v in sample_row.items():
                formatted_row[
                    short_codes.get(k)
                ] = v

        context = Context(formatted_row)
        text_body = email_template.render(context)

        return text_body

    def recipients_summary(self):
        if self.is_from_datasource():

            datasource_name = self.datasource['name']
            datasource = BulkMessage.get_datasource_object(datasource_name)

            return mark_safe(datasource.recipients_summary(self.datasource['filter']))
            return mark_safe(datasource.recipients_summary(self.datasource['filter']))
        return 'File Upload'
        
    def import_recipients_from_file(self):
        formatted_cols = self.short_codes

        if self.media:
            decoded_file = get_uploaded_file(self.media.name)
            print(decoded_file)
            
            reader = csv.DictReader(io.StringIO(decoded_file))
        
            added = 0
            for row in reader:

                print(row)
                        
                formatted_row = {}
                for k, v in row.items():
                    formatted_row[
                        formatted_cols.get(k)
                    ] = v

                if not BulkMessageRecipient.objects.filter(
                    email=formatted_row['email'],
                    bulk_message=self
                ).exists():
                    recp = BulkMessageRecipient(
                        email=formatted_row['email'],
                        bulk_message=self
                    )

                    recp.first_name = formatted_row.get('first_name', '')
                    recp.last_name = formatted_row.get('last_name', '')

                    recp.meta = formatted_row

                    try:
                        recp.save()
                        added += 1
                    except Exception as e:
                        logger.error(e)

            return added

    @property
    def formatted_short_codes(self):
        codes = self.short_codes

        result = []
        for k, v in codes.items():
            result.append( "{{" + v + "}}")

        return result

    def recipients(self):
        if self.is_from_datasource():

            datasource_name = self.datasource['name']
            datasource = BulkMessage.get_datasource_object(datasource_name)

            return datasource.data_source(self.datasource['filter'])
        else:
            recipients = BulkMessageRecipient.objects.filter(
                bulk_message=self
            )

            return recipients

    def sample_row(self):
        if self.is_from_datasource():

            datasource_name = self.datasource['name']
            datasource = BulkMessage.get_datasource_object(datasource_name)

            return datasource.sample_row()
        else:
            recps = BulkMessageRecipient.objects.filter(
                bulk_message=self
            )

            if not recps:
                return {}
        
        return recps[0].meta
    
    @classmethod
    def get_datasource_object(cls, datasource_name):
        path = 'announcement.datasources'
        try:
            if getattr(settings, 'DEBUG', False):
                ds_class = import_string(f'announcement.{path}.{datasource_name}.{datasource_name}_DS')
            else:
                ds_class = import_string(f'{path}.{datasource_name}.{datasource_name}_DS')
            return ds_class()
        except ImportError:
            print('failed to import datasource')
            return None

    def is_from_datasource(self):
        return True if self.datasource['name'] != 'file_upload' else False

    def subject(self):
        return self.meta.get('subject', 'Change me')

    @property
    def short_codes(self):
        if self.is_from_datasource():
            
            datasource_name = self.datasource['name']
            datasource = BulkMessage.get_datasource_object(datasource_name)

            return datasource.data_columns()

        if self.media:
            if not self.meta.get('short_codes'):
                sample_row = self.sample_row()
                
                if sample_row:
                    formatted_cols = {}
                    keys = list(sample_row.keys())
                    formatted_cols = self.format_cols(keys)

                    if not self.meta:
                        self.meta = {}

                    self.meta['short_codes'] = formatted_cols
                    self.save()
                else:
                    # if there are no recipients, then the short codes comes from file uploaded
                    if self.media:
                        decoded_file = get_uploaded_file(self.media.name)
                        reader = csv.DictReader(io.StringIO(decoded_file))
                    
                        formatted_cols = {}
                        for row in reader:
                            keys = row.keys()
                            formatted_cols = self.format_cols(keys)
                            
                            break
                        return formatted_cols
            return self.meta.get('short_codes')

    @property
    def ce_url(self):
        return reverse_lazy('announcements:bulk_message', kwargs={
            'record_id': self.id}
        )

class BulkMessageLog(models.Model):
    bulk_message = models.ForeignKey('announcement.BulkMessage', on_delete=models.CASCADE)
    
    run_completed_on = models.DateTimeField(blank=True, null=True)
    run_started_on = models.DateTimeField(blank=True, null=True)
    
    run_scheduled_for = models.DateTimeField(blank=True, null=True)

    meta = JSONField(default=dict)

    log_file = models.FileField(
        storage=PrivateMediaStorage(),
        blank=True,
        upload_to=bulk_message_log_upload_path
    )

    class Meta:
        ...

    @property
    def summary(self):
        return self.meta.get('summary', '')
