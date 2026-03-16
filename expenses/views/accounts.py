from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext as _
from django.db.models import Q
from django.http import JsonResponse
from itertools import chain
from ..models import Account, Transfer, Expense, Income
from ..forms import AccountForm, TransferForm

class AccountListView(LoginRequiredMixin, ListView):
    model = Account
    template_name = 'expenses/account_list.html'
    context_object_name = 'accounts'

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by('name')

class AccountCreateView(LoginRequiredMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'expenses/account_form.html'
    success_url = reverse_lazy('account-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, _("Account created successfully!"))
        return super().form_valid(form)

class AccountUpdateView(LoginRequiredMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = 'expenses/account_form.html'
    success_url = reverse_lazy('account-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, _("Account updated successfully!"))
        return super().form_valid(form)

class AccountDeleteView(LoginRequiredMixin, DeleteView):
    model = Account
    template_name = 'expenses/account_delete_confirm.html'
    success_url = reverse_lazy('account-list')

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

class AccountQuickCreateView(LoginRequiredMixin, View):
    """AJAX endpoint for creating an account from a modal and returning JSON."""

    def post(self, request):
        form = AccountForm(request.POST, user=request.user)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            return JsonResponse({
                'success': True,
                'id': account.pk,
                'name': str(account),
            })
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)


class TransferCreateView(LoginRequiredMixin, CreateView):
    model = Transfer
    form_class = TransferForm
    template_name = 'expenses/transfer_form.html'
    success_url = reverse_lazy('transfer-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, _("Transfer completed successfully!"))
        return super().form_valid(form)

class TransferListView(LoginRequiredMixin, ListView):
    model = Transfer
    template_name = 'expenses/transfer_list.html'
    context_object_name = 'transfers'

    def get_queryset(self):
        return Transfer.objects.filter(user=self.request.user).order_by('-date')

class TransferUpdateView(LoginRequiredMixin, UpdateView):
    model = Transfer
    form_class = TransferForm
    template_name = 'expenses/transfer_form.html'
    success_url = reverse_lazy('transfer-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return Transfer.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, _("Transfer updated successfully!"))
        return super().form_valid(form)

class TransferDeleteView(LoginRequiredMixin, DeleteView):
    model = Transfer
    template_name = 'expenses/transfer_confirm_delete.html'
    success_url = reverse_lazy('transfer-list')

    def get_queryset(self):
        return Transfer.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Transfer deleted successfully!"))
        return super().delete(request, *args, **kwargs)

class AccountDetailView(LoginRequiredMixin, View):
    template_name = 'expenses/account_detail.html'

    def get(self, request, pk):
        account = get_object_or_404(Account, pk=pk, user=request.user)
        
        # Get all expenses, incomes, and transfers for this account
        expenses = Expense.objects.filter(user=request.user, account=account).order_by('-date')
        incomes = Income.objects.filter(user=request.user, account=account).order_by('-date')
        
        # Transfers where this account is either FROM or TO
        transfers_from = Transfer.objects.filter(user=request.user, from_account=account)
        transfers_to = Transfer.objects.filter(user=request.user, to_account=account)
        
        # Combine everything and sort by date descending
        # We'll add a 'transaction_type' attribute to each for the template
        for e in expenses: e.transaction_type = 'EXPENSE'
        for i in incomes: i.transaction_type = 'INCOME'
        for t in transfers_from: 
            t.transaction_type = 'TRANSFER_OUT'
            t.display_amount = -t.amount
        for t in transfers_to: 
            t.transaction_type = 'TRANSFER_IN'
            t.display_amount = t.amount

        ledger = sorted(
            chain(expenses, incomes, transfers_from, transfers_to),
            key=lambda x: x.date,
            reverse=True
        )

        context = {
            'account': account,
            'ledger': ledger,
            'currency_symbol': request.user.profile.currency if hasattr(request.user, 'profile') else '₹'
        }
        return render(request, self.template_name, context)
