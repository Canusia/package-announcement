# Plan: BulkMessage Email Tracking Dashboard via SES Events

## Context

Staff send bulk emails via the announcement app. Currently there's no dashboard showing delivery stats per bulk message. The `ses_tracking` module already captures SES events (send, delivery, bounce, complaint) via SNS webhooks, but doesn't track opens/clicks and has no link back to BulkMessage records.

The goal: add a **per-BulkMessage dashboard** showing # sent, delivered, opened, bounced — visible to staff on the bulk message detail page.

## Approach

1. Tag outgoing emails with `X-BulkMessage-ID` header (mailer's `send_html_mail` already supports `headers={}`)
2. Enable Open event publishing on the AWS SES Configuration Set (`rmu-config-set`)
3. Add `open`/`click` event handling to ses_tracking webhook
4. Add a `bulk_message_id` field to `SESEvent` model, auto-extracted from the header
5. Add a tracking dashboard tab on the bulk message detail page, aggregating SESEvent counts

## Files to Modify

### 1. `announcement/models/announcement.py` — Tag outgoing emails

In `BulkMessage.send()`, pass `headers` to both `send_html_mail()` calls:

```python
headers = {'X-BulkMessage-ID': str(self.id)}

# Datasource branch (line ~283):
send_html_mail(self.subject(), text_body, html_body,
               settings.DEFAULT_FROM_EMAIL, to, headers=headers)

# File-upload branch (line ~330):
send_html_mail(self.subject(), text_body, html_body,
               settings.DEFAULT_FROM_EMAIL, to, headers=headers)
```

The existing `mark_as_opened()` and `tracking_url()` methods can remain for backward compatibility with datasource-based Note tracking — SES open tracking supplements rather than replaces them.

### 2. `ses_tracking/models.py` — Add bulk_message_id field + open event type

- Add `open` and `click` to `EVENT_TYPES` choices
- Add `bulk_message_id` field (CharField, nullable, indexed) to `SESEvent` — stores the BulkMessage UUID extracted from the `X-BulkMessage-ID` header
- Add `extract_bulk_message_id` property to parse from `raw_message.mail.headers[]`
- Update `save()` to auto-populate `bulk_message_id` on creation

```python
# New field
bulk_message_id = models.CharField(max_length=36, blank=True, null=True, db_index=True)

# New property
@property
def extract_bulk_message_id(self):
    headers = self.raw_message.get('mail', {}).get('headers', [])
    for header in headers:
        if header.get('name') == 'X-BulkMessage-ID':
            return header.get('value')
    return None
```

### 3. `ses_tracking/views.py` — Add open/click event handlers

Add `handle_open()` and `handle_click()` handlers following the existing pattern (e.g., `handle_delivery`). Route them in `sns_endpoint()`:

```python
def handle_open(message, mail_data):
    # open events have an 'open' key with userAgent, ipAddress, timestamp
    open_data = message.get('open', {})
    timestamp = open_data.get('timestamp', mail_data.get('timestamp'))
    for recipient in mail_data.get('destination', []):
        SESEvent.objects.create(
            event_type='open',
            message_id=mail_data.get('messageId', ''),
            email=recipient,
            timestamp=timestamp,
            raw_message=message,
        )
```

### 4. `ses_tracking/migrations/` — New migration

- Add `bulk_message_id` CharField to SESEvent
- Add `open` and `click` to event_type choices

### 5. `announcement/views/views.py` — Dashboard API endpoint

Add a new view `bulk_message_stats(request, record_id)` that aggregates SESEvent counts for a given BulkMessage:

```python
def bulk_message_stats(request, record_id):
    from ses_tracking.models import SESEvent
    stats = SESEvent.objects.filter(bulk_message_id=str(record_id)).values('event_type').annotate(count=Count('id'))
    result = {
        'total_sent': 0, 'total_delivered': 0,
        'total_opened': 0, 'total_bounced': 0,
        'total_complaints': 0, 'unique_opens': 0,
    }
    for s in stats:
        if s['event_type'] == 'send': result['total_sent'] = s['count']
        elif s['event_type'] == 'delivery': result['total_delivered'] = s['count']
        elif s['event_type'] == 'open': result['total_opened'] = s['count']
        elif s['event_type'] == 'bounce': result['total_bounced'] = s['count']
        elif s['event_type'] == 'complaint': result['total_complaints'] = s['count']

    result['unique_opens'] = SESEvent.objects.filter(
        bulk_message_id=str(record_id), event_type='open'
    ).values('email').distinct().count()

    return JsonResponse(result)
```

### 6. `announcement/urls/ce.py` — Add stats URL

```python
path('bulk_message/stats/<uuid:record_id>', bulk_message_stats, name='bulk_message_stats'),
```

### 7. `announcement/templates/announcements/bulk_message.html` — Dashboard tab

Add a **"Tracking"** tab (4th tab) next to "Manage Message", "Recipient(s)", "Send Log(s)":

```html
<li class="nav-item">
    <a class="nav-link" data-toggle="tab" href="#tracking">Tracking</a>
</li>
```

Tab content — summary cards + per-recipient table:

**Summary cards row:**
| Sent | Delivered | Opened | Bounced | Complaints |
|------|-----------|--------|---------|------------|
| 150  | 148       | 87 (59%) | 2     | 0          |

**Per-recipient DataTable below cards:**
| Email | Status | Opened | Bounced | Last Event |
|-------|--------|--------|---------|------------|

- Load stats via AJAX call to `bulk_message_stats` endpoint on tab click
- Per-recipient table via DRF API filtered by `bulk_message_id`

### 8. `announcement/serializers.py` — Add tracking serializer (if needed)

Serialize SESEvent records filtered by bulk_message_id for the per-recipient DataTable.

## AWS Configuration Required

In the AWS SES Console → Configuration Sets → `rmu-config-set`:
- Add event destination for **Open** and **Click** event types
- Publish to the same SNS topic already used for send/delivery/bounce events

## Verification

1. Send a test bulk email and confirm `X-BulkMessage-ID` header appears in SESEvent raw_message
2. Open the email and confirm an `open` event is received by the webhook
3. Visit the bulk message detail page, click "Tracking" tab, and verify stats display
4. Check per-recipient breakdown shows correct open/bounce status
