"""
Views for CreditCard management.
"""
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import generic

from .models import CreditCard, Expense


class CreditCardListView(LoginRequiredMixin, generic.ListView):
    """List all credit cards for the current user."""

    model = CreditCard
    template_name = "expenses/credit_card_list.html"
    context_object_name = "credit_cards"

    def get_queryset(self):
        return CreditCard.objects.filter(
            user=self.request.user, is_active=True
        ).order_by("bank_name", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cards = self.get_queryset()
        
        # Calculate totals
        context["total_credit_limit"] = cards.aggregate(
            total=Sum("credit_limit")
        )["total"] or 0
        context["total_available"] = cards.aggregate(
            total=Sum("available_limit")
        )["total"] or 0
        context["total_used"] = context["total_credit_limit"] - context["total_available"]
        
        return context


class CreditCardCreateView(LoginRequiredMixin, generic.CreateView):
    """Create a new credit card."""

    model = CreditCard
    template_name = "expenses/credit_card_form.html"
    fields = ["name", "bank_name", "credit_limit", "billing_cycle_day", "due_date_days"]
    success_url = reverse_lazy("credit-card-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Credit Card"
        context["button_text"] = "Add Card"
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        # Set available_limit equal to credit_limit for new cards
        form.instance.available_limit = form.instance.credit_limit
        messages.success(
            self.request, f'Credit card "{form.instance.name}" added successfully!'
        )
        return super().form_valid(form)


class CreditCardUpdateView(LoginRequiredMixin, generic.UpdateView):
    """Update an existing credit card."""

    model = CreditCard
    template_name = "expenses/credit_card_form.html"
    fields = ["name", "bank_name", "credit_limit", "billing_cycle_day", "due_date_days"]
    success_url = reverse_lazy("credit-card-list")

    def get_queryset(self):
        return CreditCard.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Credit Card"
        context["button_text"] = "Save Changes"
        return context

    def form_valid(self, form):
        messages.success(
            self.request, f'Credit card "{form.instance.name}" updated successfully!'
        )
        return super().form_valid(form)


class CreditCardDetailView(LoginRequiredMixin, generic.DetailView):
    """Detailed view of a credit card with billing info and transactions."""

    model = CreditCard
    template_name = "expenses/credit_card_detail.html"
    context_object_name = "card"

    def get_queryset(self):
        return CreditCard.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        card = self.object
        
        # Get transactions linked to this credit card
        context["transactions"] = Expense.objects.filter(
            user=self.request.user, credit_card=card
        ).order_by("-date")[:50]
        
        # Current billing cycle transactions
        billing_start = card.next_billing_date.replace(day=card.billing_cycle_day)
        if billing_start > date.today():
            # Go back one month
            if billing_start.month == 1:
                billing_start = billing_start.replace(year=billing_start.year - 1, month=12)
            else:
                billing_start = billing_start.replace(month=billing_start.month - 1)
        
        context["billing_start"] = billing_start
        context["billing_end"] = card.next_billing_date
        
        context["current_cycle_transactions"] = Expense.objects.filter(
            user=self.request.user,
            credit_card=card,
            date__gte=billing_start,
            date__lt=card.next_billing_date,
        ).order_by("-date")
        
        context["current_cycle_total"] = context["current_cycle_transactions"].aggregate(
            total=Sum("amount")
        )["total"] or 0
        
        return context


class CreditCardDeleteView(LoginRequiredMixin, generic.View):
    """Soft delete a credit card (set is_active=False)."""

    def post(self, request, pk):
        try:
            card = CreditCard.objects.get(pk=pk, user=request.user)
            card_name = card.name
            card.is_active = False
            card.save()
            messages.success(request, f'Credit card "{card_name}" deleted successfully!')
        except CreditCard.DoesNotExist:
            messages.error(request, "Credit card not found.")
        return redirect("credit-card-list")


class CreditCardPaymentView(LoginRequiredMixin, generic.View):
    """Record a bill payment for a credit card."""

    def post(self, request, pk):
        card = get_object_or_404(CreditCard, pk=pk, user=request.user)
        
        try:
            amount = Decimal(request.POST.get("amount", "0"))
            if amount <= 0:
                messages.error(request, "Payment amount must be positive.")
                return redirect("credit-card-detail", pk=pk)
            
            card.pay_bill(amount)
            messages.success(
                request, f'Payment of ₹{amount} recorded for "{card.name}"!'
            )
        except (ValueError, TypeError):
            messages.error(request, "Invalid payment amount.")
        
        return redirect("credit-card-detail", pk=pk)
