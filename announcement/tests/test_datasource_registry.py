from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from announcement.announcement.datasources.registry import DataSourceRegistry
from announcement.announcement.datasources.base import MyCE_BMailerDS


class _GoodDS(MyCE_BMailerDS):
    email_column = 'email'
    name_columns = ['FirstName', 'LastName']

    def data_columns(self):
        return {'first_name': 'FirstName', 'last_name': 'LastName', 'email': 'email'}


class _NoEmailDS(MyCE_BMailerDS):
    email_column = 'email'
    name_columns = ['FirstName']

    def data_columns(self):
        return {'first_name': 'FirstName'}  # missing 'email' value


class _NoNameDS(MyCE_BMailerDS):
    email_column = 'email'
    name_columns = ['FirstName']

    def data_columns(self):
        return {'email': 'email'}  # missing 'FirstName' value


class DataSourceRegistryTests(SimpleTestCase):
    def test_register_and_lookup(self):
        reg = DataSourceRegistry()
        reg.register(slug='good', title='Good DS', descriptor='a short blurb')(_GoodDS)
        self.assertIn(('good', 'Good DS'), reg.choices())
        self.assertIsInstance(reg.get('good'), _GoodDS)
        self.assertEqual(reg.descriptor('good'), 'a short blurb')

    def test_unknown_slug_returns_none(self):
        reg = DataSourceRegistry()
        self.assertIsNone(reg.get('nope'))

    def test_missing_email_column_fails_at_registration(self):
        reg = DataSourceRegistry()
        with self.assertRaises(ImproperlyConfigured):
            reg.register(slug='bad', title='Bad')(_NoEmailDS)

    def test_missing_name_column_fails_at_registration(self):
        reg = DataSourceRegistry()
        with self.assertRaises(ImproperlyConfigured):
            reg.register(slug='bad', title='Bad')(_NoNameDS)
