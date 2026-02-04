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
Pluggable recipient sources extending `MyCE_BMailerDS`:
- `highschool_admins.py` - HS administrator positions
- `teachers.py` - Teacher records
- `registration_summary_teachers.py` - Teachers with registration stats
- `registration_summary_highschools.py` - Schools with registration stats

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
