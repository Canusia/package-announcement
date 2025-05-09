import os
from django import forms
from django.template import Context, Template
from django.template.loader import get_template

from django.utils.safestring import mark_safe
from django.core.validators import RegexValidator, validate_email

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.models.section import StudentRegistration, ClassSection
from cis.models.term import Term
from cis.models.highschool import HighSchool
from cis.models.highschool_administrator import HSAdministrator, HSAdministratorPosition
from cis.models.teacher import Teacher

from .base import MyCE_BMailerDS, MyCE_BMailerForm

from cis.models.highschool_administrator import HSPosition, HSAdministratorPosition

class registration_summary_highschools_DS(MyCE_BMailerDS):

    def title(self) -> str:
        """
        Return a title for the datasource
        """
        return "Registration Summary - For High Schools"
    
    def data_filter(self, form_type='skinny', initial=None) -> str:
        """
        Creates an instance of MyCE_BMailerForm and adds options to build the filter
        """
        form = MyCE_BMailerForm(
            form_type, str(self.__class__).replace("_DS", "")
        )

        form.fields['ds_term'] = forms.ModelChoiceField(
            queryset=Term.objects.all().order_by('-code'),
            required=True,
            label='Registration Term',
            help_text=''
        )

        form.fields['ds_role'] = forms.ModelChoiceField(
            queryset=HSPosition.objects.all().order_by('name'),
            required=True,
            label='HS Administrator Position',
            help_text=''
        )

        if initial:
            form.fields['ds_term'].initial = initial.get('term')
            form.fields['ds_role'].initial = initial.get('role')

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

        sections = ClassSection.objects.filter(
            registration_term__id__in=filters.get('term')
        )

        records = HSAdministratorPosition.objects.filter(
            highschool__id__in=sections.values('highschool__id'),
            position__id__in=filters.get('role'),
            status__iexact='active'
        )

        if count:
            return records.count()

        terms = Term.objects.filter(id__in=filters.get('term'))
        for record in records:

            sections_assigned, registrations, sections_with_no_registrations, missing_payment, completed_application, missing_parent_consent = record.highschool.sections_summary(terms=terms)

            row = {
                "FirstName": record.hsadmin.user.first_name,
                "LastName": record.hsadmin.user.last_name,
                "email": [record.hsadmin.user.email],
                'highschool': record.highschool.name,
                "SectionsAssigned": sections_assigned.count(),
                "NumberOfRegistrationsRequests": registrations.count(),
                "SectionsWithNoRegistrationRequests": sections_with_no_registrations.count(),
                "MissingPayment": missing_payment.count(),
                "CompleteApplication": completed_application,
                "MissingParentConsent": missing_parent_consent,
                "AdministratorID": str(record.hsadmin.id),
                "recipient_id": str(record.hsadmin.id),
                "TermID": str(terms[0].id),
                "Term": str(terms[0]),
            }

            result.append(row)

        return result
    
    def data_columns(self) -> dict:
        """
        Returns a dict object with the values that can be used as shortcodes. Make sure the values only have alphabets and numbers.

        The value 'email' is required
        """
        return {
            "teacher_first_name": "FirstName",
            "teacher_last_name": "LastName",
            "highschool": "highschool",
            "teacher_highschool_email": "email",
            "sections_assigned" : "SectionsAssigned",
            "registrations": "NumberOfRegistrationsRequests",
            "sections_with_no_registrations" : "SectionsWithNoRegistrationRequests","missing_payment": "MissingPayment",
            "completed_application": "CompleteApplication",
            "missing_parent_consent": "MissingParentConsent",
            # "teacher_id": "TeacherID",
            "term": "Term",
        }

    def sample_row(self) -> dict:
        """
        Returns a dict keyed on data_column values. This information is used when generating a preview.
        """
        return {
            "FirstName": "John",
            "LastName": "Smith",
            "email": "teacher@highschool.edi",
            'highschool': "High School",
            "SectionsAssigned" : "2",
            "NumberOfRegistrationsRequests": "10",
            "SectionsWithNoRegistrationRequests" : "1",
            "MissingPayment": "10",
            "CompleteApplication": "5",
            "MissingParentConsent": "5",
            # "TeacherID": "abcd-abc-adbcd-ancjd",
            "Term": "Fall 2025",
        }

    def description(self) -> str:
        """
        Return a textual description of the datasource
        """
        return '<p>High Schools who are offering a section in the selected registration term</p>'

    def recipients_summary(self, filters=None) -> str:
        """
        Returns a summary of records that meet the filtering criteria.
        """
        summary = mark_safe(self.description())

        term = Term.objects.filter(
            id__in=filters.get('term')
        ).order_by('-code')
        summary += f"<p class='alert alert-info''>Filtered by Registration Term - {term[0]}<br>"
        
        records_count = self.data_source(filters, count=True)

        summary += "<br>Found " + str(records_count) + " high school administrators that meet the criteria."
        summary += "</p>"

        summary += "<h4>Customize Recipients</h4><hr>"
        summary += self.data_filter(form_type='full', initial=filters)

        return summary


    def mark_as_opened(self, recipient_id, bulk_message):
        """
        This method is called when the email is opened. It can be used to 
        track email opens or perform any other actions.
        """
        # try to find the teacher note that has bulk_message id
        # and mark it as opened
        from cis.models.note import HSAdministratorNote

        note = HSAdministratorNote.objects.filter(
            meta__bulk_message_id=str(bulk_message.id),
            hsadmin__id=recipient_id
        )

        if note.exists():
            note = note.first()
            note.meta['num_views'] += 1
            note.save()

    def post_send(self, recipient, bulk_message):
        """
        This method is called after the email is sent. It can be used to 
        perform any post-processing tasks, such as logging or updating 
        records.
        """
        # Perform any post-send actions here
        record = HSAdministrator.objects.get(
            pk=recipient.get('AdministratorID')
        )

        message = ""
        for k, v in recipient.items():
            message += f"{k}: {v}<br>"

        record.add_note(
            None,
            f"Sent {bulk_message.subject()}<br><br>{message}",
            meta={
                'type': 'private',
                'bulk_message_id': str(bulk_message.id),
                'num_views': 0,
            }
        )
