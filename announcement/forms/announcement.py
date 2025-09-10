import csv, io, datetime
from django import forms
from django.conf import settings
from django.forms import ValidationError
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.validators import validate_html_short_code, validate_cron

from form_fields import fields as FFields

from django_ckeditor_5.widgets import CKEditor5Widget as CKEditorWidget
from cis.models.customuser import CustomUser

from cis.utils import YES_NO_OPTIONS
from ..models.announcement import Announcement, BulkMessage
from ..apps import BMAILER_DS

def format_cols(columns):
    result = {}
    
    for col in columns:
        org = col[:]
        
        col = col.strip().replace(' ', '_').lower()
        
        result[org] = col
    return result

class BulkMessageFinalizeForm(forms.Form):

    title = forms.CharField(
        required=True,
        initial='Bulk Message Title',
        help_text='Internal purposes only'
    )

    action = forms.CharField(
        required=True,
        widget=forms.HiddenInput,
        initial='finalize'
    )

    status = forms.ChoiceField(
        choices=BulkMessage.STATUS_OPTIONS[:-1],
        help_text='',
        required=True
    )

    cron = forms.CharField(
        max_length=20,
        help_text='Min Hr Day Month WeekDay. Eg: 10 11 * * 1-3 to send it as 11:10am every Mon, Tue and Wed. See <a target="_blank" href="https://canusia.zendesk.com/hc/en-us/articles/24770549573527-Bulk-Messaging-Cron-Formatting-How-To-Guide">How To</a>',
        label="When should the notification be sent?",
        validators=[validate_cron]
    )

    send_after = forms.DateField(
        widget=forms.DateInput(format='%m/%d/%Y', attrs={'class':'col-md-8 col-sm-12'}),
        label='Schedule to Send Starting On',
        help_text='Select a date in the future to send.',
        input_formats=[('%m/%d/%Y')]
    )

    send_until = forms.DateField(
        widget=forms.DateInput(format='%m/%d/%Y', attrs={'class':'col-md-8 col-sm-12'}),
        label='Keep Sending Until',
        help_text='',
        input_formats=[('%m/%d/%Y')]
    )

    from_address = forms.EmailField(
        label='From Address',
        help_text='The default from address will be ' + settings.DEFAULT_FROM_EMAIL + ". In some configurations it is better to leave this unchanged.",
        required=True
    )

    def __init__(self, request, record=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request
        self.record = record

        self.helper = FormHelper()
        self.helper.form_class = 'frm_ajax'
        self.helper.form_id = 'frm_message_finalize'
        self.helper.form_method = 'POST'

        self.fields['title'].initial = record.title
        self.fields['status'].initial = record.status
        
        if not record.meta.get('from_address'):
            self.fields['from_address'].initial = settings.DEFAULT_FROM_EMAIL
        else:
            self.fields['from_address'].initial = record.meta.get('from_address')

        if record.send_on_after:
            self.fields['send_after'].initial = record.send_on_after.strftime('%m/%d/%Y')

        if record.send_until:
            self.fields['send_until'].initial = record.send_until.strftime('%m/%d/%Y')

        self.fields['cron'].initial = record.cron

        if request:
            self.helper.form_action = reverse_lazy(
                'announcements:bulk_message', args=[record.id]
            )

    def clean_status(self):
        if self.record.status == 'sent':
            raise ValidationError('The message has already been sent.')

        if not self.record.has_recipients():
            raise ValidationError('There are no recipients for this message. Please add recipients before changing status')

        return self.cleaned_data.get('status')

    def clean_send_after(self):
        data = self.cleaned_data.get('send_after')

        # if data <= datetime.date.today():
        #     raise ValidationError('Please choose a date in the future')
        return data
    
    def save(self, request, record, commit=True):
        data = self.cleaned_data

        record.title = data.get('title')
        record.status = data.get('status')
        record.send_on_after = data.get('send_after')
        record.send_until = data.get('send_until')
        record.cron = data.get('cron')

        if not record.meta:
            record.meta = {}

        record.meta['from_address'] = data.get('from_address')
        print(record.meta)
        record.save()

        return record

class BulkMessageEditorForm(forms.Form):
    
    action = forms.CharField(
        required=True,
        widget=forms.HiddenInput,
        initial='edit_message'
    )

    short_codes = FFields.ReadOnlyField(
        required=False,
        label='Customize the subject and message with the following short codes',
        widget=FFields.LongLabelWidget(
            attrs={
                'class':'border-0 bg-light h-100'
            }
        )
    )

    subject = forms.CharField(
        required=True,
        validators=[validate_html_short_code],
        widget=forms.TextInput(
            attrs={
                'class': 'col-8'
            }
        )
    )

    message = forms.CharField(
        widget=CKEditorWidget(
            attrs={"class": "django_ckeditor_5"}
        ),
        required=False,
        help_text='',
        validators=[validate_html_short_code]
    )

    def save(self, request, record, commit=True):
        data = self.cleaned_data

        record.message = data.get('message')
        
        if not record.meta:
            record.meta = {}
        record.meta['subject'] = data.get('subject')

        record.save()
        return record

    def __init__(self, request, record=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request

        self.helper = FormHelper()
        self.helper.form_class = 'frm_ajax'
        self.helper.form_id = 'frm_message_editor'
        self.helper.form_method = 'POST'

        short_codes = record.formatted_short_codes

        self.fields['short_codes'].initial = "<p class='alert alert-info'>" + ", ".join(short_codes) + "</p>"

        self.fields['subject'].initial = record.meta.get('subject')
        self.fields['message'].initial = record.message
        self.fields['message'].help_text ='<a href="#" class="float-left" onClick="preview_message(\'' + str(record.id) + '\')" >Preview Message</a><br><br>'

        if request:
            self.helper.form_action = reverse_lazy(
                'announcements:bulk_message', args=[record.id]
            )

class BulkMessageInitForm(forms.Form):
    title = forms.CharField(
        required=True,
        label='Bulk Message - Title'
    )

    id = forms.CharField(
        required=False,
        label='ID',
        widget=forms.HiddenInput
    )
    
    datasource = forms.ChoiceField(
        choices=BMAILER_DS
    )

    file = forms.FileField(
        widget=forms.FileInput(attrs={'accept': 'text/csv'}),
        label='Recipient List',
        required=False,
        help_text='CSV file must have a column with title "email"'
    )

    class Media:
        js = [
            'js/bulk_mailer.js'
        ]

    def clean_file(self):
        if self.data.get('datasource') != 'file_upload':
            return

        request = self.request

        decoded_file = request.FILES.get('file').read().decode('utf-8-sig', errors='ignore')
        reader = csv.DictReader(io.StringIO(decoded_file))
        
        try:
            for row in reader:
                col_headers = format_cols(list(row.keys()))

                if "email" not in col_headers:
                    raise ValidationError(
                        'Uploaded file needs to contain a column titled "email"'
                    )
                break
        except ValidationError as e:
            raise ValidationError(
                'Uploaded file needs to contain a column titled "email"'
            )        
        except:
            raise ValidationError('The file is not "comma delimited". Please upload a proper formatted file')

    def __init__(self, request, record=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request

        self.helper = FormHelper()
        self.helper.form_class = 'frm_ajax'
        self.helper.form_id = 'frm_add_new_bulk_message'
        self.helper.form_method = 'POST'

        self.helper.add_input(Submit('submit', 'Save and Continue'))

    def save(self, request, commit=True):

        data = self.cleaned_data
        record = BulkMessage(
            title=data.get('title'),
            createdby=request.user
        )

        record.datasource = {}
        record.datasource['name'] = data.get('datasource')
        record.datasource['filter'] = {}

        if data.get('datasource') != 'file_upload':
            for k in request.POST:
                if k.startswith('ds_'):
                    v = request.POST.getlist(k)
                    k = k.replace('ds_', '')
                
                    record.datasource['filter'][k] = v

        if request.FILES:
            record.media = request.FILES['file']

        record.meta = {}
        record.send_summary = {}

        if commit:
            record.save()

            if record.media:
                record.import_recipients_from_file()

        return record

class BulkMessageRecipientForm(BulkMessageInitForm, forms.Form):

    action = forms.CharField(
        required=True,
        widget=forms.HiddenInput,
        initial='add_recipient'
    )

    short_codes = FFields.ReadOnlyField(
        required=False,
        label='Uploading file can only have the the following column headers',
        widget=FFields.LongLabelWidget(
            attrs={
                'class':'border-0 bg-light h-100'
            }
        )
    )

    field_order = ['short_codes', 'file']

    def clean_file(self):
        request = self.request

        decoded_file = request.FILES.get('file').read().decode('utf-8-sig', errors='ignore')
        reader = csv.DictReader(io.StringIO(decoded_file))

        try:
            for row in reader:
                col_headers = format_cols(list(row.keys()))

                if "email" not in col_headers:
                    raise ValidationError(
                        'Uploaded file needs to contain a column titled "email"'
                    )
                break
            
            sample_row = self.record.sample_row()

            if not sample_row:
                return

            current_keys = list(sample_row.keys()).sort()
            new_keys = list(row.keys()).sort()

            if current_keys != new_keys:
                raise ValidationError('The new file has columns that are not the same as existing recipients.')
        except ValidationError as e:
            raise ValidationError(
                'Uploaded file needs to contain a column titled "email"'
            )
        except Exception as e:
            raise ValidationError('The file is not "comma delimited". Please upload a proper formatted file')

    def __init__(self, request, record, *args, **kwargs):
        super().__init__(request, record, *args, **kwargs)

        self.record = record
        self.request = request

        del self.fields['title']
        del self.fields['id']

        sample_row = record.sample_row()

        if not sample_row:
            self.fields['short_codes'].label = ''
            self.fields['short_codes'].initial = 'CSV file must have a column with title "email"'
        else:
            self.fields['short_codes'].initial = "<p class='alert alert-info'>" + ", ".join(sample_row.keys()) + "</p>"

    def save(self, request, record, commit=True):
        data = self.cleaned_data

        if request.FILES:
            record.media = request.FILES['file']

        if commit:
            record.save()

            record.import_recipients_from_file()

        return record

class AnnouncementForm(forms.ModelForm):

    valid_from = forms.DateField(
        widget=forms.DateInput(format='%m/%d/%Y', attrs={'class':'col-md-6 col-sm-12'}),
        input_formats=[('%m/%d/%Y')]
    )

    valid_until = forms.DateField(
        widget=forms.DateInput(format='%m/%d/%Y', attrs={'class':'col-md-6 col-sm-12'}),
        input_formats=[('%m/%d/%Y')]
    )

    def clean_valid_until(self):
        data = self.cleaned_data.get('valid_until')

        if data < self.cleaned_data.get('valid_from'):
            raise ValidationError('Please enter a valid until date')
        return data
    
    class Meta:
        model = Announcement
        fields = [
            'title',
            'description',
            'applies_to',
            'display_weight',
            'valid_from',
            'valid_until'
        ]
        required = {
            'description': False
        }

        labels = {
            'description': 'Announcement'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['description'].required = False