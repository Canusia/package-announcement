import os
from django import forms
from django.template import Context, Template
from django.template.loader import get_template

from django.core.validators import RegexValidator, validate_email
from django.utils.safestring import mark_safe

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.models.teacher import Teacher

class MyCE_BMailerForm(forms.Form):
    
    def __init__(self, form_type='skiny', datasource_name='', *args, **kwargs):
        super().__init__(*args, **kwargs)

        if form_type != 'skinny':
            self.helper = FormHelper()
            # self.helper.form_class = 'frm_ajax'
            self.helper.form_id = 'frm_update_datasource_filter'
            self.helper.form_method = 'POST'

            self.fields['datasource'] = forms.CharField(
                widget=forms.HiddenInput,
                initial=datasource_name
            )

            self.fields['action'] = forms.CharField(
                widget=forms.HiddenInput,
                initial='update_datasource_filter'
            )

            self.helper.add_input(Submit('submit', 'Save'))

class MyCE_BMailerDS:

    def description(self) -> str:
        """
        Return a textual description of the datasource
        """
        return '<p>Teachers can be selected by status. Email will sent to primary and secondary email address(es)</p>'

    def title(self) -> str:
        """
        Return a title for the datasource
        """
        return "High School Teachers - By Status"

    def data_columns(self) -> dict:
        """
        Returns a dict object with the values that can be used as shortcodes. Make sure the values only have alphabets and numbers.

        The value 'email' is required
        """
        return {
            'first_name': 'FirstName',
            'last_name': 'LastName',
            'email': 'email',
            'secondary_email': 'SecondaryEmail'
        }

    
    def sample_row(self) -> dict:
        """
        Returns a dict keyed on data_column values. This information is used when generating a preview.
        """
        return {
            'FirstName': 'Avi',
            'LastName': 'K',
            'email': 'kadaji@gmail.com',
            'SecondaryEmail': 'avi@canusia.com',
        }

    def recipients_summary(self, filters=None) -> str:
        """
        Returns a summary of records that meet the filtering criteria.
        """
        summary = mark_safe(self.description())

        summary += "<p class='alert alert-info''>Filtered by <br>"
        if filters.get('status'):
            summary += "Teacher Status(es) - " + ', '.join(filters.get('status', [])) + "<br>"

        records_count = self.data_source(filters, count=True)

        summary += "<br>Found " + str(records_count) + " teacher recipients"
        summary += "</p>"

        summary += "<h4>Customize Recipients</h4><hr>"
        summary += self.data_filter(form_type='full', initial=filters)

        return summary

    def data_filter(self, form_type='skinny', initial=None) -> str:
        """
        Creates an instance of MyCE_BMailerForm and adds options to build the filter
        """
        form = MyCE_BMailerForm(form_type, 'teachers')

        form.fields['ds_status'] = forms.MultipleChoiceField(
            choices=Teacher.STATUS_OPTIONS,
            required=True,
            label='Teacher Status',
            help_text='Select all the status that you want to send the email to',
            widget=forms.CheckboxSelectMultiple
        )

        if initial:
            form.fields['ds_status'].initial = initial.get('status')

        template = 'announcements/datasource-form.html'
        template = get_template(template)
        html = template.render({
            'form': form
        })

        return(html)

    def data_source(self, filters:dict, count=False) -> list:
        """
        Returns a list of dict items that are keyed on the values of the 
        data columns. This will be used to mail merge and send emails
        """
        result = []
        
        records = Teacher.objects.filter()
        if filters.get('status'):
            records = records.filter(
                status__in=filters['status']
            )

        if count:
            return records.count()

        for r in records:
            row = {
                'FirstName': r.user.first_name,
                'LastName': r.user.last_name,
                'email': [
                    r.user.email,
                ]
            }
            try:
                validate_email(r.user.secondary_email)
                if r.user.secondary_email:
                    row['email'].append(r.user.secondary_email)
            except:
                ...
            result.append(row)

        return result