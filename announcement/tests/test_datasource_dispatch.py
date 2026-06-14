from django.test import SimpleTestCase

from announcement.announcement.models.announcement import BulkMessage


class DatasourceDispatchTests(SimpleTestCase):
    def test_get_datasource_object_uses_registry(self):
        ds = BulkMessage.get_datasource_object('teachers')
        self.assertIsNotNone(ds)
        self.assertEqual(ds.__class__.__name__, 'teachers_DS')

    def test_unknown_datasource_returns_none(self):
        self.assertIsNone(BulkMessage.get_datasource_object('does_not_exist'))
