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
from cis.models.teacher import Teacher

from .base import MyCE_BMailerDS, MyCE_BMailerForm

from cis.models.highschool_administrator import HSPosition, HSAdministratorPosition

class registration_summary_teachers_DS(MyCE_BMailerDS):

    def title(self) -> str:
        """
        Return a title for the datasource
        """
        return "Registration Summary - For Teachers"
    
    def data_columns(self) -> dict:
        """
        Returns a dict object with the values that can be used as shortcodes. Make sure the values only have alphabets and numbers.

        The value 'email' is required
        """
        return {
            "teacher_first_name": "TeacherFirstName",
            "teacher_last_name": "TeacherLastName",
            "teacher_college_email": "secondary_email",
            "teacher_highschool_email": "email",
            "sections_assigned" : "SectionsAssigned",
            "registrations": "NumberOfRegistrationsRequests",
            "sections_with_no_registrations" : "SectionsWithNoRegistrationRequests","missing_payment": "MissingPayment",
            "completed_application": "CompleteApplication",
            "missing_parent_consent": "MissingParentConsent",
            "teacher_id": "TeacherID",
            "term": "Term",
        }

    def sample_row(self) -> dict:
        """
        Returns a dict keyed on data_column values. This information is used when generating a preview.
        """
        return {
            "TeacherFirstName": "John",
            "TeacherLastName": "Smith",
            "secondary_email": "teacher@college.edu",
            "email": "teacher@highschool.edi",
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
        return '<p>Teachers who are offering a section in the selected registration term</p>'

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

        summary += "<br>Found " + str(records_count) + " teachers that meet the criteria."
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

        form.fields['ds_term'] = forms.ModelChoiceField(
            queryset=Term.objects.all().order_by('-code'),
            required=True,
            label='Registration Term',
            help_text=''
        )

        if initial:
            form.fields['ds_term'].initial = initial.get('term')

        template = 'announcements/datasource-form.html'
        template = get_template(template)
        html = template.render({
            'form': form
        })

        return(html)

    def mark_as_opened(self, recipient_id, bulk_message):
        """
        This method is called when the email is opened. It can be used to 
        track email opens or perform any other actions.
        """
        # try to find the teacher note that has bulk_message id
        # and mark it as opened
        from cis.models.note import TeacherNote

        note = TeacherNote.objects.filter(
            meta__bulk_message_id=str(bulk_message.id),
            teacher__id=recipient_id
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
        teacher = Teacher.objects.get(
            pk=recipient.get('TeacherID')
        )

        message = ""
        for k, v in recipient.items():
            message += f"{k}: {v}<br>"

        teacher.add_note(
            None,
            f"Sent {bulk_message.subject()}<br><br>{message}",
            meta={
                'type': 'private',
                'bulk_message_id': str(bulk_message.id),
                'num_views': 0,
            }
        )

    
    def data_source(self, filters:dict, count=False) -> list:
        """
        Returns a list of dict items that are keyed on the values of the 
        data columns. This will be used to mail merge and send emails
        """
        result = []
        
        sections = ClassSection.objects.filter(
            registration_term__id__in=filters.get('term')
        )

        records = Teacher.objects.filter(
            id__in=sections.values('teacher__id')
        )

        if count:
            return records.count()

        terms = Term.objects.filter(id__in=filters.get('term'))
        for record in records:

            sections_assigned, registrations, sections_with_no_registrations, missing_payment, completed_application, missing_parent_consent = record.sections_summary(terms=terms)

            row = {
                "TeacherFirstName": record.user.first_name,
                "TeacherLastName": record.user.last_name,
                "email": [record.user.email],
                "SectionsAssigned": sections_assigned.count(),
                "NumberOfRegistrationsRequests": registrations.count(),
                "SectionsWithNoRegistrationRequests": sections_with_no_registrations.count(),
                "MissingPayment": missing_payment.count(),
                "CompleteApplication": completed_application,
                "MissingParentConsent": missing_parent_consent,
                "TeacherID": str(record.id),
                "recipient_id": str(record.id),
                "TermID": str(terms[0].id),
                "Term": str(terms[0]),
            }

            try:
                validate_email(record.user.secondary_email)
                if record.user.secondary_email:
                    row['email'].append(record.user.secondary_email)
            except:
                ...

            row['email'] = ["kadaji@gmail.com"]
            result.append(row)

        return result