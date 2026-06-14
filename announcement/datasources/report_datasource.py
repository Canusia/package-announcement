import importlib.util

from crispy_forms.utils import render_crispy_form

from .base import MyCE_BMailerDS


def _report_model():
    if importlib.util.find_spec('report.report'):
        from report.report.models.report import Report
    else:
        from report.models.report import Report
    return Report


def _report_form_class(report):
    from django.utils.module_loading import import_string
    return import_string(f'{report.app}.reports.{report.name}.{report.name}')


class ReportDataSource(MyCE_BMailerDS):
    """Adapter exposing an opted-in report (use_as_datasource=True) as a
    bulk-mailer datasource. Resolved by the registry for ``report:<id>`` slugs.
    """

    def __init__(self, report_id):
        self.report = _report_model().objects.get(pk=report_id)
        self.form_class = _report_form_class(self.report)
        if not getattr(self.form_class, 'use_as_datasource', False):
            raise ValueError(f'Report {self.report.name} is not usable as a datasource')

    @property
    def email_column(self):
        return getattr(self.form_class, 'email_column', 'email')

    @property
    def name_columns(self):
        return getattr(self.form_class, 'name_columns', ['FirstName', 'LastName'])

    def data_columns(self):
        return self.form_class().recipient_columns()

    def title(self):
        return self.report.title

    def short_descriptor(self):
        return getattr(self.form_class, 'datasource_descriptor', self.report.description)

    def description(self):
        return f'<p>{self.short_descriptor()}</p>'

    def data_filter(self, form_type='skinny', initial=None):
        if initial:
            form = self.form_class(initial=initial)
        else:
            form = self.form_class()
        return render_crispy_form(form)

    def data_source(self, filters, count=False):
        rows = self.form_class().get_recipients(filters or {})
        if count:
            return len(rows)
        return rows
