
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
        # Check for transactions due in the next 1-3 days to be robust against missed crons
        reminder_windows = [1, 2, 3]
        
        self.stdout.write(f"Checking for upcoming transactions (1-3 days out)... Today is {today}")
        
        # Get active recurring transactions
        recurring = RecurringTransaction.objects.filter(is_active=True)
        
        # Dictionary to group transactions by user for email consolidation
        user_transactions = {}
        
        count = 0
        
        for transaction in recurring:
            next_due = transaction.next_due_date
            if not next_due:
                continue
                
            days_until = (next_due - today).days
            
            if days_until in reminder_windows:
                user = transaction.user
                formatted_date = next_due.strftime("%b %d, %Y")
                
                # Per-occurrence notification title to prevent duplicates FOR THE SAME DUE DATE
                # Example: "Upcoming Expense (Due Mar 03, 2026): Rent"
                occurrence_title = f"Upcoming {transaction.transaction_type.title()} (Due {formatted_date}): {transaction.description}"
                
                # Check if we already notified for THIS SPECIFIC OCCURRENCE
                notification_exists = Notification.objects.filter(
                    user=user,
                    related_transaction=transaction,
                    title=occurrence_title
                ).exists()

                if not notification_exists:
                    user_currency = user.profile.currency if hasattr(user, 'profile') else '₹'
                    message = f"Your {transaction.frequency.lower()} {transaction.transaction_type.lower()} of {user_currency}{transaction.amount} is due on {formatted_date}."

                    # 1. Create UI Notification
                    Notification.objects.create(
                        user=user,
                        title=occurrence_title,
                        message=message,
                        related_transaction=transaction
                    )
                    
                    # 2. Send Push Notification
                    payload = {
                        "head": occurrence_title,
                        "body": message,
                        "icon": "/static/img/pwa-icon-512.png", 
                        "url": "/expenses/" 
                    }
                    try:
                        send_user_notification(user=user, payload=payload, ttl=1000)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Failed to send Push to {user}: {e}"))
                    
                    self.stdout.write(self.style.SUCCESS(f"Created notification for {transaction} (Due {formatted_date})"))
                    count += 1
                else:
                    self.stdout.write(f"Notification already exists for {transaction} on {formatted_date}")

                # 3. Add to User Group for Email (Consolidated per run)
                if user.id not in user_transactions:
                    user_transactions[user.id] = {
                        'user': user,
                        'transactions': []
                    }
                
                # Avoid adding the same transaction multiple times to the same email if it's already there
                if transaction not in user_transactions[user.id]['transactions']:
                    user_transactions[user.id]['transactions'].append(transaction)

        # 4. Send Consolidated Emails
        for user_id, data in user_transactions.items():
            user = data['user']
            transactions = data['transactions']
            
            # Robustness: Check for email
            if not user.email:
                self.stdout.write(self.style.WARNING(f"Skipping email for {user.username}: No email address"))
                continue

            # Feature Gate: Only for Plus and Pro users (using our fixed properties)
            if not hasattr(user, 'profile') or not user.profile.is_plus:
                self.stdout.write(f"Skipping email for {user.username}: Free Tier (is_plus={user.profile.is_plus if hasattr(user, 'profile') else 'N/A'})")
                continue

            self.stdout.write(f"Preparing consolidated email for {user.email} with {len(transactions)} items...")

            try:
                # Calculate total amount
                total_amount = sum(t.amount for t in transactions)
                user_currency = user.profile.currency if hasattr(user, 'profile') else '₹'
                
                context = {
                    'user': user,
                    'transactions': transactions,
                    'total_amount': total_amount,
                    'due_date': transactions[0].next_due_date, # Approximation for the template
                    'currency_symbol': user_currency
                }
                
                if len(transactions) == 1:
                    subject = f"Upcoming Payment: {transactions[0].description}"
                else:
                    subject = f"Upcoming Payments Reminder ({len(transactions)} Items)"

                html_message = render_to_string('email/recurring_reminder.html', context)
                
                send_mail(
                    subject=subject,
                    message=f"You have {len(transactions)} upcoming payments due soon. Total: {total_amount}", # Plain text fallback
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message
                )
                self.stdout.write(self.style.SUCCESS(f"Sent consolidated email to {user.email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send Email to {user.email}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully processed {count} new notifications"))

        # 5. Cleanup Old Notifications (Older than 90 days/3 months)
        cutoff_date = timezone.now() - timedelta(days=90)
        deleted_count, _ = Notification.objects.filter(created_at__lt=cutoff_date).delete()
        self.stdout.write(self.style.SUCCESS(f"Cleaned up {deleted_count} notifications older than 90 days"))
