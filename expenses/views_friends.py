from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views import generic
from datetime import date

from .models import Friend, SharedExpense, Share, Settlement


class FriendForm(forms.ModelForm):
    """Form for creating and editing friends."""

    class Meta:
        model = Friend
        fields = ["name", "email", "phone"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Friend name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "email@example.com"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+1234567890"}
            ),
        }
        help_texts = {
            "name": "Required. This name will appear in shared expenses.",
            "email": "Optional. Email address for notifications.",
            "phone": "Optional. Phone number for contact.",
        }


class SettlementForm(forms.ModelForm):
    """Form for recording a settlement payment."""

    class Meta:
        model = Settlement
        fields = ["amount", "date", "payer_is_user", "notes"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "0.00", "step": "0.01", "min": "0.01"}
            ),
            "date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "payer_is_user": forms.RadioSelect(
                choices=[(True, "I paid my friend"), (False, "My friend paid me")]
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 2, "placeholder": "Optional notes..."}
            ),
        }
        labels = {
            "payer_is_user": "Who paid?",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = date.today()


class FriendListView(LoginRequiredMixin, generic.ListView):
    """View to list all friends for the current user."""

    model = Friend
    template_name = "expenses/friend_list.html"
    context_object_name = "friends"

    def get_queryset(self):
        return Friend.objects.filter(user=self.request.user).order_by("name")


class FriendCreateView(LoginRequiredMixin, generic.CreateView):
    """View to create a new friend."""

    model = Friend
    form_class = FriendForm
    template_name = "expenses/friend_form.html"
    success_url = reverse_lazy("friend-list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(
            self.request, f'Friend "{form.instance.name}" added successfully!'
        )
        return super().form_valid(form)


class FriendUpdateView(LoginRequiredMixin, generic.UpdateView):
    """View to update an existing friend."""

    model = Friend
    form_class = FriendForm
    template_name = "expenses/friend_form.html"
    success_url = reverse_lazy("friend-list")

    def get_queryset(self):
        return Friend.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(
            self.request, f'Friend "{form.instance.name}" updated successfully!'
        )
        return super().form_valid(form)


class FriendDeleteView(LoginRequiredMixin, generic.DeleteView):
    """View to delete a friend."""

    model = Friend
    template_name = "expenses/friend_confirm_delete.html"
    success_url = reverse_lazy("friend-list")

    def delete(self, request, *args, **kwargs):
        friend_name = self.get_object().name
        messages.success(request, f'Friend "{friend_name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


class FriendDetailView(LoginRequiredMixin, generic.DetailView):
    """View to show friend details with transaction history and settlements."""

    model = Friend
    template_name = "expenses/friend_detail.html"
    context_object_name = "friend"

    def get_queryset(self):
        return Friend.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        friend = self.object

        # Get all shared expenses involving this friend
        shared_expenses = SharedExpense.objects.filter(
            participants__friend=friend
        ).distinct().select_related('expense').order_by('-expense__date')[:50]

        # Build transaction list with amounts
        transactions = []
        for se in shared_expenses:
            expense = se.expense
            payer = se.payer
            
            # Get the friend's share amount
            friend_share = Share.objects.filter(
                shared_expense=se,
                participant__friend=friend
            ).first()
            
            # Get user's share amount
            user_share = Share.objects.filter(
                shared_expense=se,
                participant__is_user=True
            ).first()
            
            if payer and payer.is_user:
                # User paid, friend owes their share
                amount = friend_share.amount if friend_share else 0
                transaction_type = 'friend_owes'
            elif payer and payer.friend == friend:
                # Friend paid, user owes their share
                amount = user_share.amount if user_share else 0
                transaction_type = 'you_owe'
            else:
                amount = 0
                transaction_type = 'neutral'

            transactions.append({
                'date': expense.date,
                'description': expense.description,
                'amount': amount,
                'type': transaction_type,
                'payer': payer.name if payer else 'Unknown',
            })

        context['transactions'] = transactions

        # Get settlements
        context['settlements'] = Settlement.objects.filter(friend=friend).order_by('-date')[:20]

        # Settlement form for quick entry
        context['settlement_form'] = SettlementForm()

        return context


class SettlementCreateView(LoginRequiredMixin, generic.CreateView):
    """View to record a settlement payment."""

    model = Settlement
    form_class = SettlementForm
    template_name = "expenses/settlement_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        friend = get_object_or_404(Friend, pk=self.kwargs['friend_pk'], user=self.request.user)
        context['friend'] = friend
        context['title'] = f"Record Settlement with {friend.name}"
        return context

    def form_valid(self, form):
        friend = get_object_or_404(Friend, pk=self.kwargs['friend_pk'], user=self.request.user)
        form.instance.user = self.request.user
        form.instance.friend = friend
        messages.success(self.request, f'Settlement with {friend.name} recorded successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('friend-detail', kwargs={'pk': self.kwargs['friend_pk']})

