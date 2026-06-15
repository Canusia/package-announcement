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

    def recipients_summary(self, filters=None):
        from django.utils.safestring import mark_safe
        filters = filters or {}
        summary = mark_safe(self.description())
        count = self.data_source(filters, count=True)
        summary += f"<p class='alert alert-info'>Found {count} recipient(s) from report '{self.title()}'.</p>"
        summary += "<h4>Filters (set when the report was used as a datasource)</h4><hr>"
        summary += self.data_filter(form_type='full', initial=filters)
        return summary

    def data_filter(self, form_type='skinny', initial=None):
        # Report datasources are display-only on the bulk-message page: the
        # filters were fixed at handoff and this form does not post back. Render
        # the report form read-only — disabled fields, no submit button, and no
        # nested <form> (so nothing here can be submitted).
        form = self.form_class(initial=initial) if initial else self.form_class()
        for field in form.fields.values():
            field.disabled = True
        helper = getattr(form, 'helper', None)
        if helper is not None:
            helper.form_tag = False
            helper.inputs = []
        return render_crispy_form(form)

    def data_source(self, filters, count=False):
        rows = self.form_class().get_recipients(filters or {})
        if count:
            return len(rows)
        return rows

    def sample_row(self):
        """Preview uses the report's own sample row (so report shortcodes show);
        falls back to the base demo row if the report doesn't define one."""
        form = self.form_class()
        if hasattr(form, 'sample_row'):
            return form.sample_row()
        return super().sample_row()
