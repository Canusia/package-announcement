# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

The Announcement app manages system announcements and bulk email campaigns for the MyCE platform. It provides role-based announcements displayed to users and a sophisticated bulk mailer with template support, scheduling, and tracking.

## Key Components

### Models (`models.py`)
- **Announcement** - Simple announcements with role-based targeting via `applies_to` field
- **BulkMessage** - Email campaigns with datasource/CSV recipients, CRON scheduling, and template shortcodes
- **BulkMessageRecipient** - Individual recipients for file-upload campaigns
- **BulkMessageLog** - Audit trail for sent campaigns with JSON logs

### Datasources (`datasources/`)
Pluggable recipient sources extending `MyCE_BMailerDS`, registered via a
**decorator-based registry** (`datasources/registry.py`, the `bmailer_datasources`
singleton — mirrors `myce.component_registry.ActionRegistry`). Built-ins:
- `highschool_admins.py` - HS administrator positions
- `teachers.py` - Teacher records
- `registration_summary_teachers.py` - Teachers with registration stats
- `registration_summary_highschools.py` - Schools with registration stats
- `report_datasource.py` - `ReportDataSource`, an adapter that exposes an opted-in
  report as a datasource (resolved dynamically for `report:<id>` slugs)

**Registering a datasource (any app):**
```python
from announcement.announcement.datasources.registry import bmailer_datasources  # or the find_spec conditional from host code
from announcement.announcement.datasources.base import MyCE_BMailerDS

@bmailer_datasources.register(slug='my_ds', title='My DS', descriptor='Short blurb.')
class my_ds_DS(MyCE_BMailerDS):
    email_column = 'email'              # contract: must be in data_columns() values
    name_columns = ['FirstName', 'LastName']   # contract: must be in data_columns() values
    def data_columns(self): ...        # {'first_name':'FirstName', ..., 'email':'email'}
    def data_source(self, filters, count=False): ...  # rows keyed by shortcode values
```
- **Decorators may live in any app.** The app eager-imports its datasource module
  in `AppConfig.ready()` (host code uses the `importlib.util.find_spec('announcement.announcement')`
  conditional import; built-ins are eager-imported in `datasources/__init__.py`).
- **Name+email contract is enforced at registration** — the registry raises
  `ImproperlyConfigured` if `email_column`/`name_columns` aren't in `data_columns()` values.
- The datasource dropdown is built dynamically from `bmailer_datasources.choices()`
  (plus a static `file_upload` entry). `BMAILER_DS` is retired.
- **Internal datasource/model/form code must use RELATIVE imports** (`from .registry`,
  `from ..datasources.base`) so it works whether the package is installed flat as
  `announcement` (prod) or nested as `announcement.announcement` (dev).

**Report as a datasource:** a report form class opts in with `use_as_datasource = True`,
a `datasource_descriptor`, `email_column`/`name_columns`, `recipient_columns()`, and
`get_recipients(self, data)` (returns name+email rows). The `report` submodule then shows
a "Use as datasource" button (gated by `settings.REPORTS_USE_AS_DATASOURCE_ENABLED`) that
POSTs to `bulk_message_use_report_as_datasource`, creating a `BulkMessage` with
`datasource = {'name': 'report:<id>', 'filter': {...lists...}}` and redirecting to the
compose page. **Handoff filters are stored as lists** (`request.POST.getlist`) — required
so the report's `status__in=` filtering works.

**Email validation:** `datasources/base.valid_emails(addresses) -> (valid, invalid)`
guards both queue insertion points (`BulkMessage.import_recipients_from_file` and
`BulkMessage.send`). Invalid addresses are skipped and recorded in the run log
(`detailed_log['invalid']` / `['skipped']`); valid recipients still send.

### URL Structure
- `/ce/announcements/` - Main management interface
- `/ce/announcements/bulk_mailer/tracker/` - Email open tracking pixel

## Architecture

**Bulk Message Workflow:**
1. Create message with datasource or CSV upload
2. Edit message content with shortcodes (e.g., `{{FirstName}}`, `{{email}}`)
3. Set CRON schedule and send window
4. Mark as `ready_to_send`
5. `send_bulk_mail` management command processes scheduled messages

**Template Variables:** Shortcodes map to datasource columns or CSV headers. Use `{{column_name}}` syntax.

## Commands

```bash
python manage.py send_bulk_mail  # Process scheduled bulk messages (run via cron)
```

## Integration

- Uses `cis.models.CustomUser` for creator tracking
- Uses `cis.storage_backend.PrivateMediaStorage` for file uploads
- Email via `mailer.send_html_mail()` with `cis/email.html` template
- Rich text editing via Django CKEditor 5

## App Configuration

Two configs for different installation modes:
- `AnnouncementConfig` - Package installation (`announcement`)
- `DevAnnouncementConfig` - Submodule installation (`announcement.announcement`)
