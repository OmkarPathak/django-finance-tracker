import calendar
from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import CharField, F, Q, Sum, Value
from django.db.models.functions import Concat
from django.views.generic import ListView

from ..models import Expense, Income, Transfer


class AllTransactionsListView(LoginRequiredMixin, ListView):
    template_name = 'expenses/all_transactions.html'
    context_object_name = 'transactions'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        
        # 1. Normalize Expenses
        expenses = Expense.objects.filter(user=user).annotate(
            type=Value('EXPENSE', output_field=CharField()),
            cat=F('category'),
            acc=F('account__name'),
            unified_amount=F('base_amount')
        ).values('pk', 'date', 'unified_amount', 'description', 'type', 'cat', 'acc', 'currency', 'amount')

        # 2. Normalize Incomes
        incomes = Income.objects.filter(user=user).annotate(
            type=Value('INCOME', output_field=CharField()),
            cat=F('source'),
            acc=F('account__name'),
            unified_amount=F('base_amount')
        ).values('pk', 'date', 'unified_amount', 'description', 'type', 'cat', 'acc', 'currency', 'amount')

        # 3. Normalize Transfers
        transfers = Transfer.objects.filter(user=user).annotate(
            type=Value('TRANSFER', output_field=CharField()),
            cat=Value('Transfer', output_field=CharField()),
            acc=Concat(F('from_account__name'), Value(' → '), F('to_account__name'), output_field=CharField()),
            unified_amount=F('converted_amount')
        ).values('pk', 'date', 'unified_amount', 'description', 'type', 'cat', 'acc')

        # Handle filtering
        search_query = self.request.GET.get('search')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        selected_years = self.request.GET.getlist('year')
        selected_months = self.request.GET.getlist('month')
        selected_types = self.request.GET.getlist('type')

        # Filter querysets individually before union if possible, or filter the union
        # Filtering individual querysets is more efficient
        if search_query:
            expenses = expenses.filter(Q(description__icontains=search_query) | Q(category__icontains=search_query))
            incomes = incomes.filter(Q(description__icontains=search_query) | Q(source__icontains=search_query))
            transfers = transfers.filter(description__icontains=search_query)

        if start_date:
            expenses = expenses.filter(date__gte=start_date)
            incomes = incomes.filter(date__gte=start_date)
            transfers = transfers.filter(date__gte=start_date)
        if end_date:
            expenses = expenses.filter(date__lte=end_date)
            incomes = incomes.filter(date__lte=end_date)
            transfers = transfers.filter(date__lte=end_date)

        if not (start_date or end_date):
            if not (selected_years or selected_months or search_query):
                selected_years = [str(datetime.now().year)]
                selected_months = [str(datetime.now().month)]
            
            if selected_years:
                expenses = expenses.filter(date__year__in=selected_years)
                incomes = incomes.filter(date__year__in=selected_years)
                transfers = transfers.filter(date__year__in=selected_years)
            if selected_months:
                expenses = expenses.filter(date__month__in=selected_months)
                incomes = incomes.filter(date__month__in=selected_months)
                transfers = transfers.filter(date__month__in=selected_months)

        # Filter by Transaction Type
        active_qs = []
        if not selected_types:
            active_qs = [expenses, incomes, transfers]
        else:
            if 'EXPENSE' in selected_types: active_qs.append(expenses)
            if 'INCOME' in selected_types: active_qs.append(incomes)
            if 'TRANSFER' in selected_types: active_qs.append(transfers)

        if not active_qs:
            return Expense.objects.none()

        # Combine using Union
        # Django union() requires all querysets to have exactly the same fields in the same order.
        # Let's ensure the fields list in values() is identical.
        fields = ('pk', 'date', 'unified_amount', 'description', 'type', 'cat', 'acc')
        
        # Re-apply values to ensure order and fields match perfectly
        normalized_qs = [qs.values(*fields) for qs in active_qs]
        
        queryset = normalized_qs[0].union(*normalized_qs[1:]).order_by('-date')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # We need the filtered querysets to calculate individual counts
        # (This is slightly redundant with get_queryset but ensures accuracy)
        search_query = self.request.GET.get('search')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        selected_years = self.request.GET.getlist('year')
        selected_months = self.request.GET.getlist('month')
        selected_types = self.request.GET.getlist('type')

        expenses = Expense.objects.filter(user=user)
        incomes = Income.objects.filter(user=user)
        transfers = Transfer.objects.filter(user=user)

        if search_query:
            expenses = expenses.filter(Q(description__icontains=search_query) | Q(category__icontains=search_query))
            incomes = incomes.filter(Q(description__icontains=search_query) | Q(source__icontains=search_query))
            transfers = transfers.filter(description__icontains=search_query)

        if start_date:
            expenses = expenses.filter(date__gte=start_date)
            incomes = incomes.filter(date__gte=start_date)
            transfers = transfers.filter(date__gte=start_date)
        if end_date:
            expenses = expenses.filter(date__lte=end_date)
            incomes = incomes.filter(date__lte=end_date)
            transfers = transfers.filter(date__lte=end_date)

        if not (start_date or end_date):
            if not (selected_years or selected_months or search_query):
                selected_years = [str(datetime.now().year)]
                selected_months = [str(datetime.now().month)]
            
            if selected_years:
                expenses = expenses.filter(date__year__in=selected_years)
                incomes = incomes.filter(date__year__in=selected_years)
                transfers = transfers.filter(date__year__in=selected_years)
            if selected_months:
                expenses = expenses.filter(date__month__in=selected_months)
                incomes = incomes.filter(date__month__in=selected_months)
                transfers = transfers.filter(date__month__in=selected_months)

        context['expense_count'] = expenses.count()
        context['income_count'] = incomes.count()
        context['transfer_count'] = transfers.count()
        context['filtered_count'] = context['expense_count'] + context['income_count'] + context['transfer_count']

        # Total amount (Base Currency)
        context['filtered_amount'] = (
            (expenses.aggregate(Sum('base_amount'))['base_amount__sum'] or 0) +
            (incomes.aggregate(Sum('base_amount'))['base_amount__sum'] or 0) +
            (transfers.aggregate(Sum('converted_amount'))['converted_amount__sum'] or 0)
        )

        # Filter options
        user_expenses = Expense.objects.filter(user=user)
        years_dates = user_expenses.dates('date', 'year', order='DESC')
        context['years'] = sorted(list(set([d.year for d in years_dates] + [datetime.now().year])), reverse=True)
        context['months_list'] = [(i, calendar.month_name[i]) for i in range(1, 13)]
        
        # Selected values
        context['selected_years'] = selected_years
        context['selected_months'] = selected_months
        context['selected_types'] = selected_types
        context['search_query'] = search_query or ''
        context['start_date'] = start_date or ''
        context['end_date'] = end_date or ''

        # Month Navigation Logic
        display_year = None
        display_month = None
        
        if len(selected_years) == 1:
            display_year = selected_years[0]
            
        if len(selected_months) == 1:
            try:
                m_idx = int(selected_months[0])
                display_month = calendar.month_name[m_idx]
            except (ValueError, IndexError):
                pass
                
        context['display_year'] = display_year
        context['display_month'] = display_month

        if len(selected_years) == 1 and len(selected_months) == 1:
            try:
                curr_year = int(selected_years[0])
                curr_month = int(selected_months[0])
                
                pm = 12 if curr_month == 1 else curr_month - 1
                py = curr_year - 1 if curr_month == 1 else curr_year
                
                nm = 1 if curr_month == 12 else curr_month + 1
                ny = curr_year + 1 if curr_month == 12 else curr_year

                from django.urls import reverse
                base_url = reverse('all-transactions')
                
                # Keep other filters (types, search)
                query_params = []
                for t in selected_types:
                    query_params.append(f'type={t}')
                if search_query:
                    query_params.append(f'search={search_query}')
                
                sort_by = self.request.GET.get('sort')
                if sort_by:
                    query_params.append(f'sort={sort_by}')
                
                qp_prev = query_params + [f'year={py}', f'month={pm}']
                qp_next = query_params + [f'year={ny}', f'month={nm}']
                
                context['prev_month_url'] = f"{base_url}?{'&'.join(qp_prev)}"
                context['next_month_url'] = f"{base_url}?{'&'.join(qp_next)}"
            except ValueError:
                pass

        return context
