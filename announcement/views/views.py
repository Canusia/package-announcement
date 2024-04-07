from django.db import IntegrityError
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.utils.safestring import mark_safe
from django.urls import reverse_lazy

from django.template.context_processors import csrf

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse

from cis.models.settings import Setting
from cis.utils import (
    user_has_cis_role, user_has_student_role,
    user_has_highschool_admin_role
)

from crispy_forms.utils import render_crispy_form

from ..models.announcement import Announcement, BulkMessage, BulkMessageRecipient, BulkMessageLog
from ..forms.announcement import (
    AnnouncementForm, BulkMessageInitForm, BulkMessageEditorForm,
    BulkMessageFinalizeForm,
    BulkMessageRecipientForm
)

from cis.menu import (
    cis_menu, draw_menu, STUDENT_MENU, HS_ADMIN_MENU
)

from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..serializers import AnnouncementSerializer, BulkMessageSerializer, BulkMessageRecipientSerializer, BulkMessageLogSerializer

class BulkMessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BulkMessageSerializer

    def get_queryset(self):
        records = BulkMessage.objects.all()
        return records

class BulkMessageLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BulkMessageLogSerializer

    def get_queryset(self):
        bulk_message_id = self.request.GET.get('bulk_message_id')

        records = BulkMessageLog.objects.all()

        if bulk_message_id:
            records = records.filter(
                bulk_message__id=bulk_message_id
            )

        return records

class BulkMessageRecipientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BulkMessageRecipientSerializer

    def get_queryset(self):
        records = BulkMessageRecipient.objects.all()
        bulk_message_id = self.request.GET.get('bulk_message_id')

        if bulk_message_id:
            records = records.filter(
                bulk_message__id=bulk_message_id
            )

        return records

class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        from datetime import datetime

        queryset = Announcement.objects.none()

        if self.request.GET.get('status', None) == 'active':
            queryset = Announcement.objects.filter(
                valid_from__lte=datetime.now(),
                valid_until__gte=datetime.now()
            )
        else:
            queryset = Announcement.objects.filter(
                
            )
        return queryset

@user_passes_test(user_has_student_role, login_url='/')
def show_announcements_for_students(request):
    return get_announcements(request, 'student')

@user_passes_test(user_has_highschool_admin_role, login_url='/')
def show_announcements_for_highschool_admin(request):
    return get_announcements(request, 'highschool_admin')

def get_announcements(request, user_role='student'):
    from datetime import datetime
    if user_role == 'student':
        applies_to = 'Students'
    elif user_role == 'highschool_admin':
        applies_to = 'High School Administrators'
    elif user_role == 'teacher':
        applies_to = 'Instructors'
    elif user_role == 'faculty':
        applies_to = 'Faculty'

    announcements = Announcement.objects.filter(
        applies_to__contains=applies_to,
        valid_from__lte=datetime.now(),
        valid_until__gte=datetime.now()
    ).order_by('display_weight')

    return announcements

@user_passes_test(user_has_cis_role, login_url='/')
def delete(request, record_id):
    record = get_object_or_404(Announcement, pk=record_id)

    try:
        record.delete()
    except Exception as e:
        messages.add_message(
            request,
            messages.SUCCESS,
            'Unable to delete record.',
            'list-group-item-danger')
        return redirect("announcements:announcement", record.id)

    messages.add_message(
        request,
        messages.SUCCESS,
        'Successfully deleted record',
        'list-group-item-success')
    return redirect("announcements:all")

from django.views.decorators.clickjacking import xframe_options_exempt
@xframe_options_exempt
@user_passes_test(user_has_cis_role, login_url='/')
def detail(request, record_id):
    '''
    Record details page
    '''
    template = 'announcements/details.html'
    record = get_object_or_404(Announcement, pk=record_id)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=record)

        if form.is_valid():
            form.save(commit=True)
            messages.add_message(
                request,
                messages.SUCCESS,
                'Successfully updated record',
                'list-group-item-success')
            return redirect('announcements:announcement', record_id=record_id)
    else:
        form = AnnouncementForm(instance=record)

    return render(
        request,
        template, {
            'form': form,
            'page_title': "Announcement",
            'labels': {
                'all_items': 'All Announcements'
            },
            'urls': {
                'all_items': 'announcements:all'
            },
            'menu': draw_menu(cis_menu, 'announcements', 'all'),
            'record': record
        })

@user_passes_test(user_has_cis_role, login_url='/')
def index(request):
    '''
     search and index page for staff
    '''
    menu = draw_menu(cis_menu, 'announcements', 'all')

    template = 'announcements/index.html'
    
    return render(
        request,
        template, {
            'page_title': 'Announcements',
            'urls': {
                'details_prefix': 'announcement/',
                'add_new': 'announcements:all'
            },
            'menu': menu,
            'add_new_form':AnnouncementForm
            }
        )

from django.views.decorators.csrf import csrf_exempt

@user_passes_test(user_has_cis_role, login_url='/')
def add_new(request):
    """
    Add new for CE Staff
    """
    ajax = request.GET.get('ajax', None)
    
    if request.method == 'POST':
        """
        Add New
        """
        if request.POST.get('action') == 'add_new_announcement':
            form = AnnouncementForm(request.POST)

            if form.is_valid():
                form.save(commit=True)

                data = {
                    'status':'success',
                    'message':'Successfully processed your request'
                }
                return JsonResponse(data)

            ctx = {}
            ctx.update(csrf(request))
            form_html = render_crispy_form(form, context=ctx)

            data = {
                'status':'error',
                'form_html':form_html,
                'message':'There was an error while completing your request. Please try again'
            }
            return JsonResponse(data)


@user_passes_test(user_has_cis_role, login_url='/')
def bulk_message_get_datasource_filters(request):
    from django.utils.module_loading import import_string
    from django.template.context_processors import csrf
    from django.template.loader import render_to_string
    from django.http import JsonResponse

    datasource_name = request.GET.get('datasource')
    datasource = BulkMessage.get_datasource_object(datasource_name)

    form_html = datasource.data_filter()
    
    return JsonResponse({
        'status': 'success',
        'filter': form_html
    })


@user_passes_test(user_has_cis_role, login_url='/')
def bulk_message_add_new(request):
    if request.method == 'POST':
        """
        Add New
        """
        form = BulkMessageInitForm(
            request=request, record=None, data=request.POST, files=request.FILES
        )

        if form.is_valid():
            record = form.save(request=request, commit=True)

            data = {
                'status':'success',
                'message':'Successfully started bulk message. Click "Okay" to continue.',
                'redirect_to': str(record.ce_url),
                'action': 'redirect_to'
            }
            return JsonResponse(data)
        else:
            return JsonResponse({
                'message': 'Please correct the errors and try again',
                'errors': form.errors.as_json()
            }, status=400)


@user_passes_test(user_has_cis_role, login_url='/')
def bulk_message_delete_all_recipients(request, record_id):
    record = get_object_or_404(BulkMessage, pk=record_id)

    if not record.can_edit:
        data = {
            'status':'error',
            'message':'Unable to clear recipients at this point'
        }
        return JsonResponse(data)

    record.bulkmessagerecipient_set.all().delete()
    record.status = 'draft'
    record.meta['short_codes'] = None

    record.save()

    data = {
        'status':'success',
        'message':'Successfully deleted all recipients. The bulk message status has been updated to "draft".',
        'action': 'reload'
    }
    return JsonResponse(data)

@user_passes_test(user_has_cis_role, login_url='/')
def bulk_message_preview(request, record_id):

    record = get_object_or_404(BulkMessage, pk=record_id)

    message = record.preview()
    return render(
        request,
        'cis/email.html',
        {
            'message': message
        }
    )

@user_passes_test(user_has_cis_role, login_url='/')
def bulk_message_delete(request, record_id):

    record = get_object_or_404(BulkMessage, pk=record_id)

    if not record.can_edit:
        return JsonResponse({
            'message': 'Unable to complete request',
            'errors': 'The bulk message has already been sent'
        }, status=400)
    
    try:
        record.delete_me()

        data = {
            'status':'success',
            'message':'Successfully deleted record.',
            'redirect_to': str(reverse_lazy('announcements:bulk_messages'))
        }
        status = 200
    except Exception as e:
        data = {
            'message': 'Unable to complete request',
            'errors': str(e)
        }
        status = 400

    return JsonResponse(data, status=status)

@csrf_exempt
@user_passes_test(user_has_cis_role, login_url='/')
def bulk_message(request, record_id):
    '''
     search and index page for staff
    '''
    menu = draw_menu(cis_menu, 'announcements', 'bulk_messages')
    template = 'announcements/bulk_message.html'
    
    record = get_object_or_404(BulkMessage, pk=record_id)
    form = BulkMessageEditorForm(request, record)
    finalize_form = BulkMessageFinalizeForm(request, record)
    recipient_form = BulkMessageRecipientForm(request, record)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_datasource_filter':
            for k in request.POST:
                if k.startswith('ds_'):
                    v = request.POST.getlist(k)
                    k = k.replace('ds_', '')
                
                    record.datasource['filter'][k] = v
            record.save()

        if action == 'add_recipient':
            form = BulkMessageRecipientForm(request, record, data=request.POST, files=request.FILES)

            if form.is_valid():
                record = form.save(request=request, record=record, commit=True)

                data = {
                    'status':'success',
                    'message':'Successfully uploaded recipient file.',
                    'redirect_to': str(record.ce_url),
                    'action': 'redirect_to'
                }
                return JsonResponse(data)
            else:
                return JsonResponse({
                    'message': 'Please correct the errors and try again',
                    'errors': form.errors.as_json()
                }, status=400)

        if action == 'finalize':
            form = BulkMessageFinalizeForm(
                request,
                record,
                request.POST
            )

            if form.is_valid():
                record = form.save(request=request, record=record, commit=True)

                data = {
                    'status':'success',
                    'message':'Successfully updated bulk message.',
                    'redirect_to': str(record.ce_url),
                    'action': 'redirect_to'
                }
                return JsonResponse(data)
            else:
                return JsonResponse({
                    'message': 'Please correct the errors and try again',
                    'errors': form.errors.as_json()
                }, status=400)

        elif action == 'edit_message':
            form = BulkMessageEditorForm(
                request=request, record=record, data=request.POST
            )

            if form.is_valid():
                record = form.save(request=request, record=record, commit=True)

                data = {
                    'status':'success',
                    'message':'Successfully saved bulk message.'
                }
                return JsonResponse(data)
            else:
                return JsonResponse({
                    'message': 'Please correct the errors and try again',
                    'errors': form.errors.as_json()
                }, status=400)

    return render(
        request,
        template, {
            'page_title': 'Bulk Message',
            'menu': menu,
            'form': form,
            'recipient_api': mark_safe(
                '/ce/announcements/api/bulk_messages_recipients?format=datatables&bulk_message_id=' + str(record.id)
            ),
            'log_api': mark_safe(
                '/ce/announcements/api/bulk_message_logs?format=datatables&bulk_message_id=' + str(record.id)
            ),
            'finalize_form': finalize_form,
            'recipient_form': recipient_form,
            'record': record
            }
        )

@user_passes_test(user_has_cis_role, login_url='/')
def bulk_messages(request):
    '''
     search and index page for staff
    '''
    menu = draw_menu(cis_menu, 'announcements', 'bulk_messages')

    template = 'announcements/bulk_messages.html'
    
    return render(
        request,
        template, {
            'page_title': 'Bulk Messages',
            'urls': {
                'details_prefix': 'announcement/',
                'add_new': 'announcements:all'
            },
            'menu': menu,
            'add_new_form': BulkMessageInitForm(request)
            }
        )

@user_passes_test(user_has_cis_role, login_url='/')
def bulk_message_logs(request):
    '''
     search and index page for staff
    '''
    menu = draw_menu(cis_menu, 'announcements', 'bulk_message_logs')

    template = 'announcements/bulk_message_logs.html'
    
    return render(
        request,
        template, {
            'page_title': 'Bulk Message Logs',
            'menu': menu
            }
        )
