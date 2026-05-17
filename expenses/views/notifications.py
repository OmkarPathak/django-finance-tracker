from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.management import call_command
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from ..models import Notification


def _cron_authorized(request):
    secret = request.GET.get('secret')
    return bool(secret and secret == settings.CRON_SECRET)


def _get_int_query_param(request, key, default):
    raw = request.GET.get(key)
    if raw in (None, ''):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _get_threshold_query_param(request, default):
    raw = request.GET.get('threshold')
    if raw in (None, ''):
        return default
    try:
        return str(float(raw))
    except (TypeError, ValueError):
        return default


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'expenses/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.objects.filter(user=self.request.user, is_read=False).count()
        return context

@login_required
def mark_notifications_read(request):
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('notification-list')
    return redirect('notification-list')

@login_required
def mark_single_notification_read(request, pk):
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

@login_required
def notification_redirect(request, pk):
    """
    Mark notification as read and redirect to its link.
    """
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        
        target_link = notification.link or 'notification-list'
        return redirect(target_link)
    except Notification.DoesNotExist:
        messages.error(request, "Notification not found.")
        return redirect('notification-list')

@csrf_exempt
def trigger_notifications(request):
    """
    HTTP endpoint to trigger notifications via external cron service.
    """
    secret = request.GET.get('secret')
    if not secret or secret != settings.CRON_SECRET:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    try:
        call_command('send_notifications')
        return JsonResponse({'success': True, 'message': 'Notifications triggered successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def trigger_lifecycle_emails(request):
    """
    HTTP endpoint to trigger lifecycle drip emails via external cron service.
    """
    secret = request.GET.get('secret')
    if not secret or secret != settings.CRON_SECRET:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        call_command('send_lifecycle_emails')
        return JsonResponse({'success': True, 'message': 'Lifecycle emails triggered successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def trigger_monthly_reports_view(request):
    """
    HTTP endpoint to trigger monthly financial reports via external cron service.
    """
    secret = request.GET.get('secret')
    if not secret or secret != settings.CRON_SECRET:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        call_command('send_monthly_report')
        return JsonResponse({'success': True, 'message': 'Monthly reports triggered successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def trigger_daily_reminders_view(request):
    """
    HTTP endpoint to trigger daily expense reminders via external cron service.
    """
    secret = request.GET.get('secret')
    if not secret or secret != settings.CRON_SECRET:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        call_command('send_daily_reminders')
        return JsonResponse({'success': True, 'message': 'Daily reminders triggered successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def trigger_ledger_retry_view(request):
    """
    HTTP endpoint to retry failed ledger shadow postings via external cron service.
    Optional query params:
    - limit (default: 200)
    """
    if not _cron_authorized(request):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    limit = _get_int_query_param(request, 'limit', 200)
    try:
        call_command('retry_ledger_shadow_failures', limit=limit)
        return JsonResponse(
            {
                'success': True,
                'message': 'Ledger retry triggered successfully',
                'limit': limit,
            }
        )
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def trigger_ledger_reconcile_view(request):
    """
    HTTP endpoint to reconcile ledger/account balances via external cron service.
    Optional query params:
    - threshold (default: 0.01)
    """
    if not _cron_authorized(request):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    threshold = _get_threshold_query_param(request, '0.01')
    try:
        call_command('reconcile_ledgers', threshold=threshold)
        return JsonResponse(
            {
                'success': True,
                'message': 'Ledger reconciliation triggered successfully',
                'threshold': threshold,
            }
        )
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def trigger_ledger_maintenance_view(request):
    """
    HTTP endpoint to run combined ledger maintenance via external cron service.
    Optional query params:
    - retry_limit (default: 200)
    - threshold (default: 0.01)
    """
    if not _cron_authorized(request):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    retry_limit = _get_int_query_param(request, 'retry_limit', 200)
    threshold = _get_threshold_query_param(request, '0.01')
    try:
        call_command(
            'run_ledger_maintenance',
            retry_limit=retry_limit,
            reconcile=True,
            threshold=threshold,
        )
        return JsonResponse(
            {
                'success': True,
                'message': 'Ledger maintenance triggered successfully',
                'retry_limit': retry_limit,
                'threshold': threshold,
            }
        )
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
