"""
Views for PaymentSource (Bank Accounts, Wallets, Cash) management.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import generic

from .models import PaymentSource, Expense


class PaymentSourceListView(LoginRequiredMixin, generic.ListView):
    """List all payment sources for the current user."""

    model = PaymentSource
    template_name = "expenses/payment_source_list.html"
    context_object_name = "payment_sources"

    def get_queryset(self):
        return PaymentSource.objects.filter(
            user=self.request.user, is_active=True
        ).order_by("account_type", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sources = self.get_queryset()
        
        # Group by type
        context["savings_accounts"] = sources.filter(account_type="savings")
        context["current_accounts"] = sources.filter(account_type="current")
        context["wallets"] = sources.filter(account_type="wallet")
        context["cash_sources"] = sources.filter(account_type="cash")
        
        # Calculate totals
        context["total_balance"] = sources.aggregate(total=Sum("balance"))["total"] or 0
        
        return context


class PaymentSourceCreateView(LoginRequiredMixin, generic.CreateView):
    """Create a new payment source."""

    model = PaymentSource
    template_name = "expenses/payment_source_form.html"
    fields = ["name", "account_type", "bank_name", "balance"]
    success_url = reverse_lazy("payment-source-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Payment Source"
        context["button_text"] = "Add Account"
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(
            self.request, f'Account "{form.instance.name}" added successfully!'
        )
        return super().form_valid(form)


class PaymentSourceUpdateView(LoginRequiredMixin, generic.UpdateView):
    """Update an existing payment source."""

    model = PaymentSource
    template_name = "expenses/payment_source_form.html"
    fields = ["name", "account_type", "bank_name", "balance"]
    success_url = reverse_lazy("payment-source-list")

    def get_queryset(self):
        return PaymentSource.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Payment Source"
        context["button_text"] = "Save Changes"
        return context

    def form_valid(self, form):
        messages.success(
            self.request, f'Account "{form.instance.name}" updated successfully!'
        )
        return super().form_valid(form)


class PaymentSourceDetailView(LoginRequiredMixin, generic.DetailView):
    """Detailed view of a payment source with transaction history."""

    model = PaymentSource
    template_name = "expenses/payment_source_detail.html"
    context_object_name = "source"

    def get_queryset(self):
        return PaymentSource.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        source = self.object
        
        # Get transactions linked to this payment source
        context["transactions"] = Expense.objects.filter(
            user=self.request.user, payment_source=source
        ).order_by("-date")[:50]
        
        # Calculate statistics
        context["total_spent"] = context["transactions"].aggregate(
            total=Sum("amount")
        )["total"] or 0
        
        return context


class PaymentSourceDeleteView(LoginRequiredMixin, generic.View):
    """Soft delete a payment source (set is_active=False)."""

    def post(self, request, pk):
        try:
            source = PaymentSource.objects.get(pk=pk, user=request.user)
            source_name = source.name
            source.is_active = False
            source.save()
            messages.success(request, f'Account "{source_name}" deleted successfully!')
        except PaymentSource.DoesNotExist:
            messages.error(request, "Account not found.")
        return redirect("payment-source-list")
