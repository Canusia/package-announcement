MyCE - Announcement
====================

- Show announcements to users by role
- Send Bulk Messages (the "bulk mailer") to recipients drawn from pluggable
  **datasources**, with template shortcodes, scheduling, and open tracking.

Install
-------

Pip-installed package (production) or in-tree editable git submodule (development).
Two app configs: ``AnnouncementConfig`` (flat ``announcement``) and
``DevAnnouncementConfig`` (nested ``announcement.announcement``).

Bulk-mailer datasources
-----------------------

A *datasource* produces the recipient list (name + email rows) for a bulk
message. Datasources subclass ``MyCE_BMailerDS`` (``datasources/base.py``) and
self-register through a decorator-based registry
(``datasources/registry.py`` → the ``bmailer_datasources`` singleton).

Register one (from any app)::

    from announcement.announcement.datasources.registry import bmailer_datasources
    from announcement.announcement.datasources.base import MyCE_BMailerDS

    @bmailer_datasources.register(slug='speakers', title='Speakers',
                                  descriptor='Users in the speaker group.')
    class speakers_DS(MyCE_BMailerDS):
        email_column = 'email'                     # must appear in data_columns() values
        name_columns = ['FirstName', 'LastName']   # must appear in data_columns() values

        def data_columns(self):
            return {'first_name': 'FirstName', 'last_name': 'LastName', 'email': 'email'}

        def data_source(self, filters, count=False):
            ...  # return rows keyed by the shortcode values; 'email' may be a list

Notes:

- **The decorator may live in any app**; eager-import the module in that app's
  ``AppConfig.ready()`` so the registration runs at startup. Host apps use the
  ``importlib.util.find_spec('announcement.announcement')`` conditional import.
- **Name + email are enforced at registration** — the registry raises
  ``ImproperlyConfigured`` if ``email_column``/``name_columns`` are missing from
  ``data_columns()`` values.
- Each datasource carries a short ``descriptor`` shown in the UI.
- The recipient dropdown is built dynamically from ``bmailer_datasources.choices()``
  (plus a static ``file_upload`` CSV option). The old ``BMAILER_DS`` list is gone.
- Internal code uses **relative imports** so it works in both flat and nested installs.

Report as a datasource
~~~~~~~~~~~~~~~~~~~~~~~~

A report (in the ``report`` framework) can be used as a datasource. The report
form class opts in with ``use_as_datasource = True``, a ``datasource_descriptor``,
``email_column``/``name_columns``, ``recipient_columns()``, and
``get_recipients(self, data)``. The reports UI then shows a "Use as datasource"
button (gated by ``settings.REPORTS_USE_AS_DATASOURCE_ENABLED``, default off) that
hands the report's filters off to the bulk mailer, pre-selecting the report as the
datasource. Resolved dynamically via the ``report:<id>`` slug → ``ReportDataSource``.

Sending & validation
~~~~~~~~~~~~~~~~~~~~~~

``send_bulk_mail`` (management command, run via cron) processes messages marked
``ready_to_send``. Email addresses are validated before queueing/sending
(``datasources/base.valid_emails``); invalid addresses are skipped and recorded in
the run log, and valid recipients still send.
