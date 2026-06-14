from django.test import TestCase, Client
from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in
import importlib.util

from cis.models.customuser import CustomUser
if importlib.util.find_spec('report.report'):
    from report.report.models.report import Report
else:
    from report.models.report import Report
from announcement.announcement.models.announcement import BulkMessage


def _login(client, user):
    from django_login_history.models import post_login
    user_logged_in.disconnect(post_login)
    try:
        client.force_login(user)
    finally:
        user_logged_in.connect(post_login)


class UseAsDatasourceHandoffTests(TestCase):
    def setUp(self):
        g, _ = Group.objects.get_or_create(name='ce')
        self.user = CustomUser.objects.create(username='ce', email='ce@x.com')
        self.user.groups.add(g)
        self.report = Report.objects.create(
            app='cis', name='teacher_certificates', title='Teacher Course Certificates',
            description='x', categories=['Instructors'], available_for=['ce'])
        self.client = Client()
        _login(self.client, self.user)

    def test_handoff_creates_bulk_message_with_report_datasource_and_list_filters(self):
        resp = self.client.post('/ce/announcements/bulk_message/use_report_as_datasource', {
            'report_id': str(self.report.id),
            'title': 'From report',
            'certificate_status': ['Teaching'],
        })
        self.assertEqual(resp.status_code, 200)
        bm = BulkMessage.objects.latest('createdon')
        self.assertEqual(bm.datasource['name'], f'report:{self.report.id}')
        # filters stored as LISTS (so get_recipients filtering works)
        self.assertEqual(bm.datasource['filter'].get('certificate_status'), ['Teaching'])
