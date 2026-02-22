import json
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import UserProfile, PaymentHistory, SubscriptionPlan
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@login_required
def create_order(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            plan_type = data.get('plan_type')
            duration = data.get('duration', 'YEARLY')

            if duration not in ('MONTHLY', 'YEARLY'):
                return JsonResponse({'error': 'Invalid duration'}, status=400)

            try:
                plan_obj = SubscriptionPlan.objects.get(tier=plan_type, duration=duration, is_active=True)
            except SubscriptionPlan.DoesNotExist:
                 return JsonResponse({'error': 'Invalid or inactive plan'}, status=400)

            # Amount in paise
            amount_in_paise = int(plan_obj.price * 100)
            
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            order_data = {
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': f'receipt_order_{request.user.id}_{int(timezone.now().timestamp())}',
                'notes': {
                    'plan': plan_type,
                    'duration': duration,
                    'user_id': request.user.id
                }
            }
            
            order = client.order.create(data=order_data)
            
            # Save order details
            PaymentHistory.objects.create(
                user=request.user,
                order_id=order['id'],
                amount=plan_obj.price,
                tier=plan_type,
                duration=duration,
                status='PENDING'
            )

            return JsonResponse(order)
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
@login_required
def verify_payment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_signature = data.get('razorpay_signature')

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            # Verify Signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            try:
                client.utility.verify_payment_signature(params_dict)
            except razorpay.errors.SignatureVerificationError:
                PaymentHistory.objects.filter(order_id=razorpay_order_id).update(status='FAILED')
                return JsonResponse({'error': 'Signature Verification Failed'}, status=400)

            # Payment Successful
            # Update PaymentHistory
            payment_record = PaymentHistory.objects.get(order_id=razorpay_order_id)
            payment_record.payment_id = razorpay_payment_id
            payment_record.status = 'SUCCESS'
            payment_record.save()
            
            # Update User Subscription
            profile = request.user.profile
            profile.tier = payment_record.tier
            profile.razorpay_order_id = razorpay_order_id
            
            # Set end date based on duration
            if payment_record.duration == 'MONTHLY':
                profile.subscription_end_date = timezone.now() + timedelta(days=30)
            else:
                profile.subscription_end_date = timezone.now() + timedelta(days=365)
            profile.save()

            return JsonResponse({'success': True})
        except PaymentHistory.DoesNotExist:
             return JsonResponse({'error': 'Order not found'}, status=404)
        except Exception as e:
            logger.error(f"Error verifying payment: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=405)
