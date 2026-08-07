from unittest.mock import patch

from django.test import TestCase

from cis.models.customuser import CustomUser

from announcement.announcement.models.announcement import (
    BulkMessage,
    BulkMessageRecipient,
)

CSV = 'first_name,last_name,email\r\nSusana,Vel\xe1zquez,s@x.org\r\nJoe,Dea,j@y.org\r\n'


class ImportRecipientsFromFileTests(TestCase):
    """Covers the path behind "upload said success but showed no recipients"."""

    def setUp(self):
        self.user = CustomUser.objects.create(username='ce', email='ce@x.com')
        self.record = BulkMessage.objects.create(
            createdby=self.user,
            datasource={'name': 'file_upload', 'filter': {}},
            meta={},
        )
        # import_recipients_from_file only runs when a file is attached; the
        # bytes themselves come back through get_uploaded_file, which is patched
        # per-test below.
        self.record.media = 'bulk_message/media/test.csv'
        self.record.save()

    def _import(self, content):
        target = 'announcement.announcement.models.announcement.get_uploaded_file'
        with patch(target, return_value=content):
            return self.record.import_recipients_from_file()

    def test_imports_every_row(self):
        self.assertEqual(self._import(CSV), 2)
        self.assertEqual(
            BulkMessageRecipient.objects.filter(bulk_message=self.record).count(), 2
        )

    def test_accented_name_is_preserved(self):
        self._import(CSV)
        recp = BulkMessageRecipient.objects.get(
            bulk_message=self.record, email='s@x.org'
        )
        self.assertEqual(recp.last_name, 'Vel\xe1zquez')

    def test_unreadable_file_reports_zero_rather_than_crashing(self):
        # get_uploaded_file returns None when the object is missing or unreadable.
        self.assertEqual(self._import(None), 0)
        self.assertEqual(
            BulkMessageRecipient.objects.filter(bulk_message=self.record).count(), 0
        )

    def test_reimporting_the_same_file_adds_nothing(self):
        self._import(CSV)
        self.assertEqual(self._import(CSV), 0)
