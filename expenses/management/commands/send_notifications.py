
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from expenses.models import RecurringTransaction, Notification
from webpush import send_user_notification
from datetime import timedelta

class Command(BaseCommand):
    help = 'Sends notifications for recurring transactions due in 3 days'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        target_date = today + timedelta(days=3)
        
        self.stdout.write(f"Checking for transactions due on {target_date}...")
        
        # Get active recurring transactions
        recurring = RecurringTransaction.objects.filter(is_active=True)
        
        # Dictionary to group transactions by user for email consolidation
        # Format: { user_id: { 'user': user_obj, 'transactions': [tx1, tx2] } }
        user_transactions = {}
        
        count = 0
        
        for transaction in recurring:
            # We need to check if the *next* due date matches target_date
            if transaction.next_due_date == target_date:
                user = transaction.user
                
                # Prevent duplicate notifications for the same transaction and date
                # We check if a notification was created for this transaction in the last 24 hours 
                yesterday = timezone.now() - timedelta(days=1)
                if Notification.objects.filter(
                    related_transaction=transaction, 
                    created_at__gte=yesterday,
                    title__contains="Upcoming"
                ).exists():
                    self.stdout.write(f"Skipping duplicate for {transaction}")
                    continue

                title = f"Upcoming {transaction.transaction_type.title()}: {transaction.description}"
                formatted_date = transaction.next_due_date.strftime("%b %d, %Y")
                message = f"Your {transaction.frequency.lower()} {transaction.transaction_type.lower()} of {settings.CURRENCY_SYMBOL if hasattr(settings, 'CURRENCY_SYMBOL') else '₹'}{transaction.amount} is due on {formatted_date}."

                # 1. Create UI Notification (Keep granular)
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    related_transaction=transaction
                )
                
                # 2. Send Push Notification (Keep granular for now, or could consolidate)
                payload = {
                    "head": title,
                    "body": message,
                    "icon": "/static/img/pwa-icon-512.png", 
                    "url": "/expenses/" 
                }
                try:
                    send_user_notification(user=user, payload=payload, ttl=1000)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Failed to send Push to {user}: {e}"))

                # 3. Add to User Group for Email
                if user.id not in user_transactions:
                    user_transactions[user.id] = {
                        'user': user,
                        'transactions': []
                    }
                user_transactions[user.id]['transactions'].append(transaction)
                
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Processed notification for {transaction}"))

        # 4. Send Consolidated Emails
        for user_id, data in user_transactions.items():
            user = data['user']
            transactions = data['transactions']
            
            # Feature Gate: Only for Plus and Pro users
            if not hasattr(user, 'profile') or not user.profile.is_plus:
                self.stdout.write(f"Skipping email for {user.username} (Free Tier)")
                continue

            try:
                # Calculate total amount (rough sum, assuming same currency)
                total_amount = sum(t.amount for t in transactions)
                
                context = {
                    'user': user,
                    'transactions': transactions,
                    'total_amount': total_amount,
                    'due_date': target_date,
                    'currency_symbol': settings.CURRENCY_SYMBOL if hasattr(settings, 'CURRENCY_SYMBOL') else '₹'
                }
                
                if len(transactions) == 1:
                    subject = f"Upcoming Payment: {transactions[0].description}"
                else:
                    subject = f"Upcoming Payments Reminder ({len(transactions)} Items)"

                html_message = render_to_string('email/recurring_reminder.html', context)
                
                send_mail(
                    subject=subject,
                    message=f"You have {len(transactions)} upcoming payments due on {target_date}. Total: {total_amount}", # Plain text fallback
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message
                )
                self.stdout.write(self.style.SUCCESS(f"Sent consolidated email to {user.email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send Email to {user}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully processed {count} transactions"))

        # 5. Cleanup Old Notifications (Older than 90 days/3 months)
        cutoff_date = timezone.now() - timedelta(days=90)
        deleted_count, _ = Notification.objects.filter(created_at__lt=cutoff_date).delete()
        self.stdout.write(self.style.SUCCESS(f"Cleaned up {deleted_count} notifications older than 90 days"))
