"""Bulk mailer reliability (#4): scheduled sends aren't skipped between cron
runs, one failing message doesn't stop the run, announcements match the
portal's role exactly, and datasources this tenant can't support are hidden."""
import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from announcement.announcement.datasources.base import MyCE_BMailerDS
from announcement.announcement.datasources.registry import DataSourceRegistry
from announcement.announcement.management.commands import send_bulk_mail
from announcement.announcement.models.announcement import (
    Announcement, BulkMessage, BulkMessageLog,
)
from announcement.announcement.views import views

DAY = datetime.date(2026, 10, 24)


def at(hour, minute, day=DAY):
    return datetime.datetime.combine(day, datetime.time(hour, minute))


class _Base(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username='ce@x.com', email='ce@x.com')

    def message(self, send_time='10:01 AM', dates=None, **meta):
        bm = BulkMessage.objects.create(
            title='Reminder', createdby=self.user, status='ready_to_send',
            datasource={'name': 'file_upload'},
            meta={'send_dates': dates or DAY.strftime('%m/%d/%Y'),
                  'send_time': send_time, **meta})
        return bm


@override_settings(MYCE_CRON_INTERVAL=9)
class ScheduleTests(_Base):
    def test_time_between_two_runs_is_sent_by_the_next_run(self):
        bm = self.message('10:01 AM')
        # runs at 10:00:30 and 10:10:30; the old 9-minute window missed 10:01
        self.assertIsNone(bm.due_send_date(at(10, 0)))
        self.assertEqual(bm.due_send_date(at(10, 10)), DAY)

    def test_sent_once_per_date(self):
        bm = self.message('10:01 AM')
        self.assertEqual(bm.claim_send_date(at(10, 10)), DAY)
        self.assertIsNone(bm.claim_send_date(at(10, 20)))
        bm.refresh_from_db()
        self.assertEqual(bm.meta['sent_on_dates'], [DAY.isoformat()])

    def test_each_send_date_is_sent(self):
        nxt = DAY + datetime.timedelta(days=1)
        bm = self.message('10:01 AM', dates=f"{DAY:%m/%d/%Y}, {nxt:%m/%d/%Y}")
        self.assertEqual(bm.claim_send_date(at(10, 10)), DAY)
        self.assertEqual(bm.claim_send_date(at(10, 10, nxt)), nxt)

    def test_late_night_time_is_sent_after_midnight(self):
        bm = self.message('11:58 PM')
        self.assertEqual(bm.due_send_date(at(0, 5, DAY + datetime.timedelta(days=1))), DAY)

    def test_not_sent_long_after_its_time(self):
        bm = self.message('10:01 AM')
        self.assertIsNone(bm.due_send_date(at(14, 0)))

    def test_not_ready_or_bad_meta_is_not_due(self):
        self.assertIsNone(self.message(send_time='').due_send_date(at(10, 10)))
        self.assertIsNone(self.message('25:00').due_send_date(at(10, 10)))
        bm = self.message()
        bm.status = 'draft'
        self.assertIsNone(bm.due_send_date(at(10, 10)))

    @override_settings(MYCE_CRON_INTERVAL='9')
    def test_cron_interval_from_env_is_a_string(self):
        self.assertEqual(self.message().due_send_date(at(10, 10)), DAY)

    @override_settings(MYCE_CRON_INTERVAL=60, BMAILER_SEND_GRACE_MINUTES=30)
    def test_grace_is_at_least_two_cron_intervals(self):
        self.assertEqual(self.message().due_send_date(at(11, 50)), DAY)


class RunTests(_Base):
    def test_one_failing_message_does_not_stop_the_others(self):
        bad, good = self.message(), self.message()
        sent = []

        def fake_send(bm):
            if bm.pk == bad.pk:
                raise RuntimeError('datasource broke')
            sent.append(bm.pk)
            return 'ok', {'success': [], 'fail': []}

        with mock.patch.object(BulkMessage, 'claim_send_date', return_value=DAY), \
                mock.patch.object(BulkMessage, 'send', fake_send), \
                mock.patch.object(BulkMessageLog.log_file.field.storage, 'save',
                                  return_value='log.json'), \
                self.assertLogs(send_bulk_mail.logger, 'ERROR') as logs:
            send_bulk_mail.Command().handle()

        self.assertEqual(sent, [good.pk])
        self.assertIn('Traceback', logs.output[0])
        failed = BulkMessageLog.objects.get(bulk_message=bad)
        self.assertIn('failed - datasource broke', failed.summary)

    def test_message_not_due_is_skipped(self):
        self.message()
        with mock.patch.object(BulkMessage, 'claim_send_date', return_value=None), \
                mock.patch.object(BulkMessage, 'send') as send:
            send_bulk_mail.Command().handle()
        send.assert_not_called()


class AnnouncementRoleTests(_Base):
    def announce(self, applies_to):
        return Announcement.objects.create(
            title=applies_to, description='x', applies_to=applies_to.split(','),
            valid_from=datetime.date(2000, 1, 1), valid_until=datetime.date(2999, 1, 1))

    def titles(self, role, request=None):
        return {a.title for a in views.get_announcements(request, role)}

    def test_only_the_portals_role_counts(self):
        self.announce('student')
        self.announce('instructor')
        request = RequestFactory().get('/')
        request.user = self.user  # roles don't matter, the portal does
        self.assertEqual(self.titles('student', request), {'student'})
        self.assertEqual(self.titles('teacher', request), {'instructor'})

    def test_roles_match_whole_values(self):
        self.announce('tech_center_staff')
        self.announce('highschool_admin,ce')
        self.assertEqual(self.titles('ce'), {'highschool_admin,ce'})
        self.assertEqual(self.titles('staff'), set())

    def test_user_with_no_groups_gets_no_error(self):
        request = RequestFactory().get('/')
        request.user = self.user
        self.assertEqual(self.titles('student', request), set())


class AddNewMethodTests(_Base):
    def test_get_is_405(self):
        for view in (views.add_new, views.bulk_message_add_new):
            request = RequestFactory().get('/')
            request.user = self.user
            with mock.patch.object(views, 'user_has_cis_role', return_value=True):
                response = view.__wrapped__(request)
            self.assertEqual(response.status_code, 405, view.__name__)


class _DS(MyCE_BMailerDS):
    def data_columns(self):
        return {'first_name': 'FirstName', 'last_name': 'LastName', 'email': 'email'}


class _MissingSchemaDS(_DS):
    @classmethod
    def is_available(cls):
        return False


class DatasourceOptOutTests(SimpleTestCase):
    def registry(self):
        reg = DataSourceRegistry()
        reg.register(slug='a', title='A')(_DS)
        reg.register(slug='b', title='B')(_DS)
        reg.register(slug='c', title='C')(_MissingSchemaDS)
        return reg

    def test_unavailable_datasource_is_hidden(self):
        self.assertEqual([s for s, _ in self.registry().choices()], ['a', 'b'])

    @override_settings(BMAILER_DISABLED_DATASOURCES=['b'])
    def test_tenant_can_disable_a_datasource(self):
        self.assertEqual([s for s, _ in self.registry().choices()], ['a'])

    def test_unregister(self):
        reg = self.registry()
        reg.unregister('a')
        reg.unregister('missing')
        self.assertEqual([s for s, _ in reg.choices()], ['b'])
        self.assertIsNone(reg.get('a'))

    def test_builtins_check_the_schema_they_need(self):
        from announcement.announcement.datasources import (
            registration_summary_highschools as hs, registration_summary_teachers as rt,
            teachers,
        )
        self.assertTrue(teachers.teachers_DS.is_available())
        with mock.patch.object(rt, 'has_field', return_value=False):
            self.assertFalse(rt.registration_summary_teachers_DS.is_available())
        with mock.patch.object(hs, 'has_field', return_value=False):
            self.assertFalse(hs.registration_summary_highschools_DS.is_available())
        with mock.patch.object(teachers, 'has_field', return_value=False):
            self.assertFalse(teachers.teachers_DS.is_available())


class TestEmailFilterTests(TestCase):
    def test_test_email_missing_from_saved_filter(self):
        from announcement.announcement.datasources.registration_summary_teachers import (
            registration_summary_teachers_DS as ds,
        )
        for initial in ({'term': None, 'mode': 'live'}, {'test_email': []},
                        {'test_email': 'a@x.com'}):
            ds().data_filter(initial=initial)  # must not raise
