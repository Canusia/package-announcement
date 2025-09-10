import logging, datetime, json
from django.core.management import call_command
from django.core.management.base import BaseCommand

from django.utils.timezone import make_aware
from django.conf import settings

logger = logging.getLogger(__name__)

from django.utils import timezone
from django.core.files.base import ContentFile, File

from ...models.announcement import BulkMessage, BulkMessageLog
# from ..models.announcement import BulkMessage, BulkMessageLog
class Command(BaseCommand):
    '''
    Daily jobs
    '''
    help = ''

    def handle(self, *args, **kwargs):
        # get all 'ready to send' messages

        ready_messages = BulkMessage.objects.filter(
            status='ready_to_send',
            send_on_after__lte=make_aware(datetime.datetime.now()),
            send_until__gte=timezone.now()
        )
        
        for bm in ready_messages:
            # check if they are ready to send in current run window
            if bm.should_message_be_sent():
                log = BulkMessageLog(
                    bulk_message=bm,
                    run_started_on=make_aware(datetime.datetime.now())
                )
                
                # send message
                summary, detailed_log = bm.send()
                log.run_completed_on = make_aware(datetime.datetime.now())

                log.meta = {}
                log.meta['summary'] = summary

                log.log_file.save('log.json', ContentFile(
                    json.dumps(detailed_log).encode())
                )

                log.save()
            else:
                print(f'{bm} no need to send now')