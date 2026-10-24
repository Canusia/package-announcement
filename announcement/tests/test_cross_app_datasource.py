from django.test import SimpleTestCase

from announcement.announcement.datasources.registry import bmailer_datasources
import cis.bmailer_datasources  # noqa: F401  (registers the cis datasource)


class CrossAppDatasourceTests(SimpleTestCase):
    def test_cis_datasource_is_registered(self):
        slugs = dict(bmailer_datasources.choices())
        self.assertIn('cis_speakers', slugs)
        ds = bmailer_datasources.get('cis_speakers')
        self.assertIsNotNone(ds)
