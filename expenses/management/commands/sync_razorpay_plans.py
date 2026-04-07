import razorpay
from django.conf import settings
from django.core.management.base import BaseCommand
from expenses.models import SubscriptionPlan
from finance_tracker.plans import PLAN_DETAILS

class Command(BaseCommand):
    help = 'Sync plans from finance_tracker/plans.py to Razorpay and local database'

    def handle(self, *args, **options):
        # Check if settings are available
        if not hasattr(settings, 'RAZORPAY_KEY_ID') or not hasattr(settings, 'RAZORPAY_KEY_SECRET'):
            self.stdout.write(self.style.ERROR('RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not set in settings'))
            return

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        for tier, details in PLAN_DETAILS.items():
            if tier == 'FREE':
                continue
            
            plan_name = details.get('name')
            
            # Monthly
            self.sync_plan(client, tier, 'MONTHLY', plan_name, details.get('price_monthly'))
            
            # Yearly
            self.sync_plan(client, tier, 'YEARLY', plan_name, details.get('price_yearly'))

    def sync_plan(self, client, tier, duration, name, price):
        if price is None or price <= 0:
            return

        # Check if plan already synced in DB
        db_plan, created = SubscriptionPlan.objects.get_or_create(
            tier=tier,
            duration=duration,
            defaults={'name': f'{name} ({duration.capitalize()})', 'price': price}
        )
        
        if not db_plan.razorpay_plan_id:
            try:
                # Create Plan on Razorpay
                period = 'monthly' if duration == 'MONTHLY' else 'yearly'
                
                razor_plan_data = {
                    "period": period,
                    "interval": 1,
                    "item": {
                        "name": f"{name} {duration.capitalize()}",
                        "amount": int(price * 100), # in paise
                        "currency": "INR",
                        "description": f"{duration.capitalize()} subscription for {name} plan"
                    }
                }
                
                razor_plan = client.plan.create(data=razor_plan_data)
                db_plan.razorpay_plan_id = razor_plan['id']
                db_plan.price = price # Sync price just in case
                db_plan.save()
                self.stdout.write(self.style.SUCCESS(f'Successfully created Razorpay plan for {tier} {duration}: {razor_plan["id"]}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating Razorpay plan for {tier} {duration}: {str(e)}'))
        else:
             # Just update price if needed in DB
            if db_plan.price != price:
                db_plan.price = price
                db_plan.save()
                self.stdout.write(self.style.WARNING(f'Updated price for existing plan {tier} {duration} in DB (Razorpay plan not updated)'))
            self.stdout.write(self.style.SUCCESS(f'Plan {tier} {duration} already synced: {db_plan.razorpay_plan_id}'))
