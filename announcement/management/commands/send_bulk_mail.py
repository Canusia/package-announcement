import logging, datetime, json
from django.core.management.base import BaseCommand

from django.utils.timezone import make_aware

logger = logging.getLogger(__name__)

from django.core.files.base import ContentFile

from ...models.announcement import BulkMessage, BulkMessageLog


class Command(BaseCommand):
    '''
    Send the 'ready to send' bulk messages that are due.

    Each message is sent on its own: one that fails is logged and the run
    moves on to the next.
    '''
    help = ''

    def handle(self, *args, **kwargs):
        ready_messages = BulkMessage.objects.filter(
            status='ready_to_send'
        )

        for bm in ready_messages:
            try:
                self.send_one(bm)
            except Exception:
                logger.exception('Bulk message %s (%s) failed to send', bm.pk, bm)

    def send_one(self, bm):
        # claimed before sending, so a failed send is not retried for that date
        send_date = bm.claim_send_date()
        if send_date is None:
            return

        log = BulkMessageLog(
            bulk_message=bm,
            run_started_on=make_aware(datetime.datetime.now())
        )

        try:
            summary, detailed_log = bm.send()
        except Exception as e:
            log.run_completed_on = make_aware(datetime.datetime.now())
            log.meta = {'summary': f'<br>Send for {send_date:%m/%d/%Y} failed - {e}'}
            log.save()
            raise

        log.run_completed_on = make_aware(datetime.datetime.now())
        log.meta = {'summary': summary}

        log.log_file.save('log.json', ContentFile(
            json.dumps(detailed_log).encode())
        )

        log.save()
