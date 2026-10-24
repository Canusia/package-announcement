from django.test import SimpleTestCase

from announcement.announcement.datasources.report_datasource import ReportDataSource


class _StubForm:
    use_as_datasource = True
    def sample_row(self):
        return {'CRN': '999', 'email': 'stub@example.com'}


class ReportSampleRowDelegationTests(SimpleTestCase):
    def test_sample_row_uses_report_form_when_available(self):
        ds = ReportDataSource.__new__(ReportDataSource)   # bypass __init__/DB
        ds.form_class = _StubForm
        self.assertEqual(ds.sample_row(), {'CRN': '999', 'email': 'stub@example.com'})

    def test_sample_row_falls_back_to_base_when_form_has_none(self):
        class _NoSample:
            use_as_datasource = True
        ds = ReportDataSource.__new__(ReportDataSource)
        ds.form_class = _NoSample
        # base MyCE_BMailerDS.sample_row returns the teacher demo dict
        self.assertIn('email', ds.sample_row())
