from django.test import SimpleTestCase

from announcement.announcement.datasources.base import valid_emails


class EmailValidationHelperTests(SimpleTestCase):
    def test_filters_invalid_addresses(self):
        valid, invalid = valid_emails(['a@x.com', 'not-an-email', 'b@y.org'])
        self.assertEqual(valid, ['a@x.com', 'b@y.org'])
        self.assertEqual(invalid, ['not-an-email'])

    def test_accepts_single_string(self):
        valid, invalid = valid_emails('a@x.com')
        self.assertEqual(valid, ['a@x.com'])
        self.assertEqual(invalid, [])

    def test_all_invalid(self):
        valid, invalid = valid_emails(['nope', ''])
        self.assertEqual(valid, [])
        self.assertEqual(invalid, ['nope', ''])
