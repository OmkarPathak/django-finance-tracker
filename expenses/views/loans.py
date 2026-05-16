from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from ..forms import LoanForm, LoanInterestRateForm, LoanRepaymentForm
from ..models import Loan, LoanInterestRate, LoanRepayment
from ..services import LoanService


class LoanListView(LoginRequiredMixin, ListView):
    model = Loan
    template_name = 'expenses/loan_list.html'
    context_object_name = 'loans'

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user).order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loans = self.get_queryset()
        
        loan_summaries = []
        total_debt = 0
        for loan in loans:
            summary = LoanService.get_loan_summary(loan)
            summary['loan'] = loan
            summary['progress'] = (summary['principal_paid'] / float(loan.initial_principal) * 100) if loan.initial_principal > 0 else 0
            loan_summaries.append(summary)
            total_debt += summary['remaining_principal']
            
        context['loan_summaries'] = loan_summaries
        context['total_debt'] = total_debt
        return context

class LoanCreateView(LoginRequiredMixin, CreateView):
    model = Loan
    form_class = LoanForm
    template_name = 'expenses/loan_form.html'
    success_url = reverse_lazy('loan-list')

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.user = self.request.user
            self.object = form.save()
            # Create initial interest rate
            LoanInterestRate.objects.create(
                loan=self.object,
                interest_rate=form.cleaned_data['interest_rate'],
                effective_date=self.object.start_date
            )
        messages.success(self.request, _("Loan created successfully!"))
        return redirect(self.success_url)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class LoanUpdateView(LoginRequiredMixin, UpdateView):
    model = Loan
    form_class = LoanForm
    template_name = 'expenses/loan_form.html'
    success_url = reverse_lazy('loan-list')

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            # Update initial interest rate if it changed and is the only one
            rates = self.object.interest_rates.all()
            if rates.count() == 1:
                rate = rates.first()
                rate.interest_rate = form.cleaned_data['interest_rate']
                rate.save()
        messages.success(self.request, _("Loan updated successfully!"))
        return redirect(self.success_url)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class LoanDeleteView(LoginRequiredMixin, DeleteView):
    model = Loan
    success_url = reverse_lazy('loan-list')

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Loan deleted successfully."))
        return super().delete(request, *args, **kwargs)

class LoanDetailView(LoginRequiredMixin, View):
    template_name = 'expenses/loan_detail.html'

    def get(self, request, pk):
        loan = get_object_or_404(Loan, pk=pk, user=request.user)
        summary = LoanService.get_loan_summary(loan)
        schedule = LoanService.generate_amortization_schedule(loan)
        repayments = loan.repayments.all().order_by('-date')
        
        repayment_form = LoanRepaymentForm(user=request.user, loan=loan)
        rate_form = LoanInterestRateForm()
        
        context = {
            'loan': loan,
            'summary': summary,
            'schedule': schedule,
            'repayments': repayments,
            'repayment_form': repayment_form,
            'rate_form': rate_form,
        }
        return render(request, self.template_name, context)

class LoanRepaymentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        loan = get_object_or_404(Loan, pk=pk, user=request.user)
        form = LoanRepaymentForm(request.POST, user=request.user, loan=loan)
        if form.is_valid():
            try:
                repayment = form.save(commit=False)
                repayment.loan = loan
                repayment.save()
                messages.success(request, _("Repayment recorded successfully!"))
            except (RuntimeError, ValidationError):
                messages.error(request, _("Unable to record repayment because currency conversion failed or repayment data is invalid."))
        else:
            messages.error(request, _("Error recording repayment. Please check the form."))
        return redirect('loan-detail', pk=pk)

class LoanInterestRateCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        loan = get_object_or_404(Loan, pk=pk, user=request.user)
        form = LoanInterestRateForm(request.POST)
        if form.is_valid():
            rate = form.save(commit=False)
            rate.loan = loan
            rate.save()
            messages.success(request, _("Interest rate updated successfully!"))
        else:
            messages.error(request, _("Error updating interest rate."))
        return redirect('loan-detail', pk=pk)
class LoanRepaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = LoanRepayment

    def get_queryset(self):
        return LoanRepayment.objects.filter(loan__user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Repayment deleted successfully."))
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        return reverse_lazy('loan-detail', kwargs={'pk': self.object.loan.pk})
