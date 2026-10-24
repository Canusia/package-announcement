from collections import OrderedDict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class DataSourceRegistry:
    """Registry of bulk-mailer datasources.

    Datasource classes self-register via the ``register`` decorator, which can
    be used from any app. Mirrors myce.component_registry.ActionRegistry.
    """

    def __init__(self):
        self._datasources = OrderedDict()

    def register(self, slug, title, descriptor=''):
        """Decorator: register a MyCE_BMailerDS subclass under ``slug``.

        Enforces the recipient contract at registration: the class's
        ``email_column`` and every ``name_columns`` entry must appear in the
        values of ``data_columns()``.
        """
        def decorator(cls):
            self._validate_contract(slug, cls)
            self._datasources[slug] = {
                'class': cls,
                'title': title,
                'descriptor': descriptor,
            }
            return cls
        return decorator

    @staticmethod
    def _validate_contract(slug, cls):
        try:
            columns = set(cls().data_columns().values())
        except Exception as exc:  # noqa: BLE001 - surface any contract problem
            raise ImproperlyConfigured(
                f"Datasource '{slug}' could not be inspected: {exc}")

        email_col = getattr(cls, 'email_column', None)
        name_cols = getattr(cls, 'name_columns', None)
        if not email_col or email_col not in columns:
            raise ImproperlyConfigured(
                f"Datasource '{slug}' must expose its email_column "
                f"('{email_col}') in data_columns() values.")
        if not name_cols:
            raise ImproperlyConfigured(
                f"Datasource '{slug}' must declare name_columns.")
        missing = [c for c in name_cols if c not in columns]
        if missing:
            raise ImproperlyConfigured(
                f"Datasource '{slug}' name_columns {missing} are not in "
                f"data_columns() values.")

    def unregister(self, slug):
        """Remove ``slug``; a no-op if it isn't registered."""
        self._datasources.pop(slug, None)

    def is_enabled(self, slug):
        """False when the tenant lists ``slug`` in BMAILER_DISABLED_DATASOURCES,
        or the datasource reports this tenant's schema can't support it."""
        entry = self._datasources.get(slug)
        if not entry:
            return False
        if slug in getattr(settings, 'BMAILER_DISABLED_DATASOURCES', ()):
            return False
        return entry['class'].is_available()

    def choices(self):
        """[(slug, title)] of the enabled datasources, for the dropdown."""
        return [(slug, e['title']) for slug, e in self._datasources.items()
                if self.is_enabled(slug)]

    def get(self, slug):
        """Return an instance for ``slug``, or None.

        ``report:<id>`` slugs resolve to a ReportDataSource (added later).
        """
        if slug and slug.startswith('report:'):
            from .report_datasource import ReportDataSource
            return ReportDataSource(slug.split(':', 1)[1])
        entry = self._datasources.get(slug)
        return entry['class']() if entry else None

    def descriptor(self, slug):
        entry = self._datasources.get(slug)
        return entry['descriptor'] if entry else ''

    def title(self, slug):
        entry = self._datasources.get(slug)
        return entry['title'] if entry else ''


# Singleton other apps import and decorate against.
bmailer_datasources = DataSourceRegistry()
