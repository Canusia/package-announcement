import os
from django import forms
from django.template import Context, Template
from django.template.loader import get_template

from django.utils.safestring import mark_safe
from django.core.validators import RegexValidator, validate_email

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.models.teacher import Teacher

from .base import MyCE_BMailerDS, MyCE_BMailerForm

from cis.models.highschool_administrator import HSPosition, HSAdministratorPosition

class highschool_admins_DS(MyCE_BMailerDS):

    def data_columns(self) -> dict:
        """
        Returns a dict object with the values that can be used as shortcodes. Make sure the values only have alphabets and numbers.

        The value 'email' is required
        """
        return {
            'first_name': 'FirstName',
            'last_name': 'LastName',
            'email': 'email',
            'highschool': 'HighSchool',
            # 'secondary_email': 'SecondaryEmail',
            'position': 'PositionTitle'
        }

    def sample_row(self) -> dict:
        """
        Returns a dict keyed on data_column values. This information is used when generating a preview.
        """
        return {
            'FirstName': 'Avi',
            'LastName': 'K',
            'email': 'kadaji@gmail.com',
            'HighSchool': 'HS 1',
            # 'SecondaryEmail': 'avi@canusia.com',
            'PositionTitle': 'Pincipal'
        }

    def description(self) -> str:
        """
        Return a textual description of the datasource
        """
        return '<p>School administrators selected by role and status. Email will sent to primary email address(es)</p>'

    def title(self) -> str:
        """
        Return a title for the datasource
        """
        return "High School Administrators - By Role & Status"
    
    def recipients_summary(self, filters=None) -> str:
        """
        Returns a summary of records that meet the filtering criteria.
        """
        summary = mark_safe(self.description())

        summary += "<p class='alert alert-info''>Filtered by <br><br>"
        if filters.get('role'):
            role_names = HSPosition.objects.filter(
                id__in=filters.get('role')
            ).order_by(
                'name'
            ).values_list('name', flat=True)
            summary += "HS Role(s) - " + ', '.join(role_names) + "<br>"

        if filters.get('status'):
            summary += "HS Position Status(es) - " + ', '.join(filters.get('status', [])) + "<br>"

        records_count = self.data_source(filters, count=True)

        summary += "<br>Found " + str(records_count) + " school administrators"
        summary += "</p>"

        summary += "<h4>Customize Recipients</h4><hr>"
        summary += self.data_filter(form_type='full', initial=filters)

        return summary

    def data_filter(self, form_type='skinny', initial=None) -> str:
        """
        Creates an instance of MyCE_BMailerForm and adds options to build the filter
        """
        form = MyCE_BMailerForm(
            form_type, str(self.__class__).replace("_DS", "")
        )

        form.fields['ds_role'] = forms.ModelMultipleChoiceField(
            queryset=HSPosition.objects.all().order_by('name'),
            required=True,
            label='Role(s)',
            help_text='Select all the roles that you want to send the email to',
            widget=forms.CheckboxSelectMultiple
        )

        form.fields['ds_status'] = forms.MultipleChoiceField(
            choices=HSAdministratorPosition.STATUS_OPTIONS,
            required=True,
            label='Role Status',
            help_text='Select all the status that you want to send the email to',
            widget=forms.CheckboxSelectMultiple
        )

        if initial:
            form.fields['ds_role'].initial = initial.get('role')
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
        
        records = HSAdministratorPosition.objects.filter()
        if filters.get('status'):
            records = records.filter(
                status__in=filters['status']
            )

        if filters.get('role'):
            records = records.filter(
                position__id__in=filters['role']
            )

        if count:
            return records.count()

        for r in records:
            row = {
                'FirstName': r.user.first_name,
                'LastName': r.user.last_name,
                'email': [
                    r.user.email,
                ],
                'HighSchool': r.highschool.name,
                'PositionTitle': r.position.name
            }
            try:
                validate_email(r.user.secondary_email)
                if r.user.secondary_email:
                    row['email'].append(r.user.secondary_email)
            except:
                ...
            result.append(row)

        return result