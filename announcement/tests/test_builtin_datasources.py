from django.test import SimpleTestCase

from announcement.announcement.datasources.registry import bmailer_datasources
import announcement.announcement.datasources  # noqa: F401  (triggers registration)


class BuiltinDatasourceRegistrationTests(SimpleTestCase):
    def test_all_builtins_registered_with_descriptor(self):
        slugs = dict(bmailer_datasources.choices())
        for slug in ('teachers', 'highschool_admins',
                     'registration_summary_teachers',
                     'registration_summary_highschools'):
            self.assertIn(slug, slugs, f'{slug} not registered')
            self.assertTrue(bmailer_datasources.descriptor(slug),
                            f'{slug} has no descriptor')

    def test_get_returns_instance(self):
        self.assertIsNotNone(bmailer_datasources.get('teachers'))
