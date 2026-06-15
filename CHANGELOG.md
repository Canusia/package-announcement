# Changelog

All notable changes to **myce_announcement** (the MyCE Announcement & Bulk Mailer
package) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Releases use CalVer: `YYYY.MAJOR.MINOR`.

## [2026.3.0] — 2026-06-15

Major release: the bulk mailer gains a pluggable datasource registry and the
ability to drive campaigns from any opted-in report.

### Added
- **Datasource registry.** `DataSourceRegistry` (`datasources/registry.py`,
  `bmailer_datasources` singleton) with a `@bmailer_datasources.register(slug,
  title, descriptor)` decorator. The datasource dropdown is built dynamically
  from `bmailer_datasources.choices()`. Datasources may be registered from any
  app (the host registers a cross-app datasource in `cis`).
- **Name + email contract** enforced at registration: the registry raises
  `ImproperlyConfigured` if a datasource's `email_column` / `name_columns` are
  not present in its `data_columns()` values.
- **Report as a datasource.** A report form opts in with `use_as_datasource =
  True` (+ `datasource_descriptor`, `email_column`/`name_columns`,
  `recipient_columns()`, `get_recipients()`). `ReportDataSource` adapts such a
  report for `report:<id>` slugs.
- **Report → datasource handoff** endpoint that creates a `BulkMessage` from a
  report and carries the report's filters (stored as lists so `status__in=`
  style filtering works).
- **Rich preview shortcodes.** `ReportDataSource.sample_row()` delegates to the
  report form, so the compose-page preview shows the report's own shortcode
  tokens instead of the generic demo row.
- **Email validation** (`datasources/base.valid_emails`) guarding both queue
  insertion points (`import_recipients_from_file`, `send`); invalid addresses
  are skipped and recorded in the run log, valid recipients still send.
- Documentation of the registry, report-as-datasource, and email validation
  (`CLAUDE.md`, `README.rst`).

### Changed
- Bulk-mailer datasources are now dispatched through the registry; the static
  `BMAILER_DS` map is retired.
- Report-datasource filters render read-only on the bulk-message page (the
  filters are fixed at handoff and the form does not post back).
- Internal datasource/model/form code uses **relative imports** so the package
  works whether installed flat as `announcement` (production) or nested as
  `announcement.announcement` (editable submodule).

### Fixed
- **Per-tenant migration churn on `Announcement.applies_to`.** The field's
  `choices` are built at runtime from each tenant's `settings.MY_CE` roles, so
  `makemigrations` baked tenant-specific role labels into this shared package's
  migrations (`0001` carried one tenant's labels; every other tenant wanted its
  own). Choices have no effect on the database and the role keys are identical
  across tenants, so this was pure churn that leaked configuration between
  tenants. A new `RoleMultiSelectField` drops `choices` in `deconstruct()` and
  pins the base `multiselectfield` import path, producing a single, stable,
  tenant-neutral migration (`0002_alter_announcement_applies_to`) that never
  churns again and is independent of the install layout.

### Migrations
- `announcement.0002_alter_announcement_applies_to` — choices-only `AlterField`;
  a no-op against the database (the column is unchanged `varchar(300)`), safe to
  apply on every tenant.

## [2026.2.0] — 2026-02-06

### Changed
- Packaging/refactor merge (PR #1): editable-submodule install support
  (`DevAnnouncementConfig` for the nested `announcement.announcement` layout
  alongside `AnnouncementConfig` for the flat install). Content-identical to
  `2026.1.0`.

## [2026.1.0] — 2026-02-06

### Added
- Initial release: role-based announcements and the bulk mailer (template
  shortcodes, CRON scheduling, send tracking, CSV/datasource recipients).

[2026.3.0]: https://github.com/Canusia/package-announcement/releases/tag/2026.3.0
[2026.2.0]: https://github.com/Canusia/package-announcement/releases/tag/2026.2.0
[2026.1.0]: https://github.com/Canusia/package-announcement/releases/tag/2026.1.0
