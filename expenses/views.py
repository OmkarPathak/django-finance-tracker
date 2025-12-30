from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
import csv
from django.forms import modelformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic import TemplateView
from django.db.models import Sum, Q
from .models import Expense, Category, Income
from .forms import ExpenseForm, IncomeForm
import pandas as pd
from datetime import datetime, date
import calendar


# Custom signup view to log user in immediately
class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

@login_required
def home_view(request):
    """
    Dashboard view with filters and multiple charts.
    """
    # Base QuerySet
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    
    # Filter Logic
    # Filter Logic
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')
    selected_category = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Date Range takes precedence
    if start_date or end_date:
        if start_date:
            expenses = expenses.filter(date__gte=start_date)
        if end_date:
            expenses = expenses.filter(date__lte=end_date)
        
        # Reset year/month selection for UI clarity since we are in custom range mode
        selected_year = None
        selected_month = None
        
        trend_title = "Expenses Trend (Custom Range)"
    else:
        # Default to current month/year if nothing selected
        if selected_year is None:
            selected_year = datetime.now().year
        if selected_month is None:
            selected_month = datetime.now().month
        
        if selected_year:
            expenses = expenses.filter(date__year=selected_year)
        if selected_month:
            expenses = expenses.filter(date__month=selected_month)
            
        if selected_month and selected_year:
            trend_title = f"Daily Expenses for {selected_month}/{selected_year}"
        else:
            trend_title = "Monthly Expenses Trend"

    if selected_category:
        expenses = expenses.filter(category=selected_category)
    if selected_category:
        expenses = expenses.filter(category=selected_category)
        
    # Income Logic (Mirroring Expense Filters)
    incomes = Income.objects.filter(user=request.user)
    if start_date or end_date:
        if start_date:
            incomes = incomes.filter(date__gte=start_date)
        if end_date:
            incomes = incomes.filter(date__lte=end_date)
    else:
        if selected_year:
            incomes = incomes.filter(date__year=selected_year)
        if selected_month:
            incomes = incomes.filter(date__month=selected_month)
    
    total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or 0
    all_dates = Expense.objects.filter(user=request.user).dates('date', 'year', order='DESC')
    years = [d.year for d in all_dates]
    all_categories = Expense.objects.filter(user=request.user).values_list('category', flat=True).distinct().order_by('category')

    # 1. Category Chart Data (Distribution) & Summary Table
    # We need to fetch raw values and merge them in Python to handle whitespace duplicates
    raw_category_data = expenses.values('category').annotate(total=Sum('amount'))
    
    # Process and merge duplicates
    merged_category_map = {}
    for item in raw_category_data:
        # Strip whitespace to normalize
        cat_name = item['category'].strip()
        amount = float(item['total'])
        
        if cat_name in merged_category_map:
            merged_category_map[cat_name] += amount
        else:
            merged_category_map[cat_name] = amount
            
    # Convert back to list of dicts for template/charts, sorted by total
    # This replaces the DB-ordered queryset with a sorted list
    category_data = [
        {'category': cat, 'total': amt} 
        for cat, amt in merged_category_map.items()
    ]
    category_data.sort(key=lambda x: x['total'], reverse=True)

    # Compute limits and usage per category for chart display
    category_limits = []
    for item in category_data:
        try:
            cat_obj = Category.objects.get(user=request.user, name=item['category'])
            limit = float(cat_obj.limit) if cat_obj.limit else None
        except Category.DoesNotExist:
            limit = None
        used_percent = round((item['total'] / limit * 100), 1) if limit else None
        category_limits.append({
            'name': item['category'],
            'total': item['total'],
            'limit': limit,
            'used_percent': used_percent,
        })
    
    categories = [item['category'] for item in category_data]
    category_amounts = [item['total'] for item in category_data]
    
    # 2. Time Trend (Stacked) Data
    from django.db.models.functions import TruncMonth, TruncDay
    
    # Determine Labels (X-Axis)
    # Determine Labels (X-Axis)
    if start_date or end_date:
        # For custom range, if range < 60 days, show daily. Else monthly.
        # Simple heuristic: Always show daily for custom range for now, or let logic decide.
        # Let's stick to: if explicit month selected -> daily. If range -> daily (usually granular).
        trend_qs = expenses.annotate(period=TruncDay('date'))
        date_format = '%d %b'
    elif selected_month and selected_year:
        # Daily view
        trend_qs = expenses.annotate(period=TruncDay('date'))
        date_format = '%d %b'
    else:
        # Monthly view
        trend_qs = expenses.annotate(period=TruncMonth('date'))
        date_format = '%b %Y'

    # Aggregate by Period AND Category for Stacking
    stacked_data = trend_qs.values('period', 'category').annotate(total=Sum('amount')).order_by('period')
    
    # Process into Chart.js Datasets
    # 1. Get unique sorted periods
    periods = sorted(list(set(item['period'] for item in stacked_data)))
    trend_labels = [p.strftime(date_format) for p in periods]
    
    # 2. Build datasets map: { 'CategoryA': [0, 10, 0...], 'CategoryB': ... }
    # Initialize with zeros for all unique NORMALIZED categories found in expenses
    normalized_all_categories = sorted(list(merged_category_map.keys()))
    dataset_map = { cat: [0] * len(periods) for cat in normalized_all_categories }
    
    for item in stacked_data:
        p_idx = periods.index(item['period'])
        # Strip to match our normalized keys
        cat = item['category'].strip()
        if cat in dataset_map:
            dataset_map[cat][p_idx] += float(item['total']) # Add += in case multiple unstripped cats map to same striped cat in same period
            
    # 3. Convert map to list of dataset objects for Chart.js
    trend_datasets = []
    # Define a color palette (Light Blue, Blue Green, Prussian Blue, Honey Yellow, Orange)
    colors = ['#8ECAE6', '#219EBC', '#023047', '#FFB703', '#FB8500']
    
    for i, (cat, data) in enumerate(dataset_map.items()):
        # Only include non-zero datasets
        if sum(data) > 0:
             trend_datasets.append({
                 'label': cat,
                 'data': data,
                 'backgroundColor': colors[i % len(colors)],
                 'borderRadius': 2
             })

    # 3. Top 5 Expenses
    top_expenses_qs = expenses.order_by('-amount')[:5]
    top_labels = [e.description[:20] + '...' if len(e.description) > 20 else e.description for e in top_expenses_qs]
    top_amounts = [float(e.amount) for e in top_expenses_qs]

    # 4. Summary Stats
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    transaction_count = expenses.count()
    top_category = category_data[0] if category_data else None
    
    savings = total_income - total_expenses
    
    context = {
        'total_income': total_income,
        'savings': savings,
        'recent_transactions': expenses.order_by('-date')[:5],
        'categories': categories,
        'category_amounts': category_amounts,
        'category_data': category_data, # Passing full queryset for the summary table
        'category_limits': category_limits,
        'trend_labels': trend_labels,
        'trend_datasets': trend_datasets,
        'trend_title': trend_title,
        'top_labels': top_labels,
        'top_amounts': top_amounts,
        'years': years,
        'all_categories': all_categories,
        'selected_year': int(selected_year) if selected_year else None,
        'selected_month': int(selected_month) if selected_month else None,
        'selected_category': selected_category,
        'months_list': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'total_expenses': total_expenses,
        'transaction_count': transaction_count,
        'top_category': top_category,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'home.html', context)

@login_required
def upload_view(request):
    """
    Upload view with year selection enforcement.
    """
    if request.method == 'POST' and request.FILES.get('file'):
        excel_file = request.FILES['file']
        selected_year = int(request.POST.get('year'))
        
        try:
            # Read all sheets
            xls = pd.ExcelFile(excel_file)
            for sheet_name in xls.sheet_names:
                # Read with header=None to manually find the header row
                df_raw = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                
                # Search for the header row
                header_row_index = -1
                for i, row in df_raw.head(10).iterrows():
                    row_values = [str(val).strip().title() for val in row.values]
                    if 'Date' in row_values and 'Amount' in row_values and 'Description' in row_values:
                        header_row_index = i
                        break
                
                if header_row_index == -1:
                    print(f"Skipping sheet {sheet_name}: Could not find header row.")
                    continue

                # Reload dataframe with correct header
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=header_row_index)
                
                # Normalize columns
                df.columns = [str(col).strip().title() for col in df.columns]
                
                required_columns = ['Date', 'Amount', 'Description', 'Category']
                if not all(col in df.columns for col in required_columns):
                    print(f"Skipping sheet {sheet_name}: Missing required columns.")
                    continue

                for index, row in df.iterrows():
                    # Parse date
                    date_val = row['Date']
                    if pd.isna(date_val):
                        continue
                        
                    # Handle different date formats or datetime objects
                    date_obj = None
                    if isinstance(date_val, str):
                        formats = ['%d %b %Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y', '%d %B %Y', '%d %b', '%d-%b', '%d %B']
                        for fmt in formats:
                            try:
                                parsed_date = datetime.strptime(date_val, fmt).date()
                                # Force year
                                date_obj = parsed_date.replace(year=selected_year)
                                break
                            except ValueError:
                                continue
                        if not date_obj:
                            print(f"Skipping row {index}: Could not parse date '{date_val}'")
                            continue
                    else:
                        date_obj = date_val.date() if hasattr(date_val, 'date') else date_val
                        # Force year
                        try:
                            date_obj = date_obj.replace(year=selected_year)
                        except ValueError:
                            # Handle Feb 29 on non-leap year target
                             # Fallback to Feb 28 or Mar 1
                             date_obj = date_obj.replace(day=28, year=selected_year)

                    # Get other fields
                    amount = row['Amount']
                    description = row['Description']
                    category = row['Category']
                    
                    if pd.isna(amount) or pd.isna(description):
                        continue

                    # Auto-create category if it doesn't exist
                    if category:
                        # Ensure category is a string
                        category_name = str(category).strip()
                        if category_name:
                            Category.objects.get_or_create(user=request.user, name=category_name)
                            category = category_name # Use standardized name

                    # Upsert (Get or Create to avoid duplicates)
                    Expense.objects.get_or_create(
                        user=request.user,
                        date=date_obj,
                        amount=amount,
                        description=description,
                        category=category
                    )
            return redirect('home')
        except Exception as e:
            print(f"Error processing file: {e}")
            import traceback
            traceback.print_exc()
            pass

    # Context for year dropdown
    current_year = datetime.now().year
    years = range(current_year, current_year - 5, -1)
    
    return render(request, 'upload.html', {'years': years, 'current_year': current_year})

class ExpenseListView(LoginRequiredMixin, generic.ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 20

    def get_queryset(self):
        queryset = Expense.objects.filter(user=self.request.user).order_by('-date')
        
        # Filtering
        year = self.request.GET.get('year')
        month = self.request.GET.get('month')
        category = self.request.GET.get('category')
        search_query = self.request.GET.get('search')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        # Date Range Logic (Precedence over Year/Month)
        if start_date or end_date:
            if start_date:
                queryset = queryset.filter(date__gte=start_date)
            if end_date:
                queryset = queryset.filter(date__lte=end_date)
        else:
            # Standard Year/Month Logic
            if year is None:
                year = datetime.now().year
                queryset = queryset.filter(date__year=year)
            elif year:
                queryset = queryset.filter(date__year=year)
            if month:
                queryset = queryset.filter(date__month=month)
        if category:
            queryset = queryset.filter(category=category)
        if search_query:
            queryset = queryset.filter(description__icontains=search_query)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get unique years and categories for validation
        user_expenses = Expense.objects.filter(user=self.request.user)
        years = user_expenses.dates('date', 'year', order='DESC')
        categories = user_expenses.values_list('category', flat=True).distinct().order_by('category')
        
        context['years'] = years
        context['categories'] = categories
        context['months_list'] = [(i, calendar.month_name[i]) for i in range(1, 13)]
        
        # Determine selected year for UI
        # Determine selected year for UI
        year_param = self.request.GET.get('year')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        context['start_date'] = start_date
        context['end_date'] = end_date
        
        if start_date or end_date:
            context['selected_year'] = None
        elif year_param is None:
            context['selected_year'] = datetime.now().year
        elif year_param:
            try:
                context['selected_year'] = int(year_param)
            except ValueError:
                context['selected_year'] = None
        else:
            context['selected_year'] = None
            
        return context

class ExpenseCreateView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'expenses/expense_form.html'

    def get(self, request, *args, **kwargs):
        # We need to wrap the formset to pass 'user' to the form constructor
        ExpenseFormSet = modelformset_factory(Expense, form=ExpenseForm, extra=3, can_delete=True)
        # Pass user to form kwargs using formset_factory's form_kwargs (requires Django 4.0+)
        # For older Django or modelformset, we might need a custom formset or curry the form.
        # Simpler approach: Use a lambda or partial, but modelformset_factory creates a class.
        
        # Actually, best way for modelformset with custom init args is to override BaseFormSet or manually iterate.
        # But simpler hack: Set the widget choices in the view by iterating forms? No, new forms need it.
        
        # Let's use form_kwargs in the formset initialization if supported.
        # Django 1.9+ supports form_kwargs in formset constructor.
        
        initial_data = [{'date': datetime.now().date()} for _ in range(3)]
        formset = ExpenseFormSet(queryset=Expense.objects.none(), initial=initial_data, form_kwargs={'user': request.user})
        return render(request, self.template_name, {'formset': formset})

    def post(self, request, *args, **kwargs):
        ExpenseFormSet = modelformset_factory(Expense, form=ExpenseForm, extra=3, can_delete=True)
        formset = ExpenseFormSet(request.POST, form_kwargs={'user': request.user})
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.user = request.user
                instance.save()
            return redirect('expense-list')
        return render(request, self.template_name, {'formset': formset})

class ExpenseUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expense-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        # Ensure user can only edit their own expenses
        return Expense.objects.filter(user=self.request.user)

class ExpenseDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expense-list')

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)
    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

class CategoryListView(LoginRequiredMixin, generic.ListView):
    model = Category
    template_name = 'expenses/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).order_by('name')

class CategoryCreateView(LoginRequiredMixin, generic.CreateView):
    model = Category
    fields = ['name', 'limit']
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('category-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class CategoryUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Category
    fields = ['name', 'limit']
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('category-list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        # Store old name to update related expenses
        old_name = self.get_object().name
        response = super().form_valid(form)
        new_name = self.object.name
        
        if old_name != new_name:
            Expense.objects.filter(user=self.request.user, category=old_name).update(category=new_name)
            
        return response

class CategoryDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Category
    template_name = 'expenses/category_confirm_delete.html'
    success_url = reverse_lazy('category-list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

@login_required
def export_expenses(request):
    """
    Export expenses to CSV based on current filters.
    """
    expenses = Expense.objects.filter(user=request.user).order_by('-date')

    # Filter Logic (Duplicate of ExpenseListView logic)
    year = request.GET.get('year')
    month = request.GET.get('month')
    category = request.GET.get('category')
    search_query = request.GET.get('search')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date or end_date:
        if start_date:
            expenses = expenses.filter(date__gte=start_date)
        if end_date:
            expenses = expenses.filter(date__lte=end_date)
    else:
        if year is None:
            year = datetime.now().year
            expenses = expenses.filter(date__year=year)
        elif year:
            expenses = expenses.filter(date__year=year)
        if month:
            expenses = expenses.filter(date__month=month)

    if category:
        expenses = expenses.filter(category=category)
    if search_query:
        expenses = expenses.filter(description__icontains=search_query)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expenses.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Category', 'Description', 'Amount'])

    for expense in expenses:
        writer.writerow([expense.date, expense.category, expense.description, expense.amount])

# --------------------
# Income Views
# --------------------

class IncomeListView(LoginRequiredMixin, generic.ListView):
    model = Income
    template_name = 'expenses/income_list.html'
    context_object_name = 'incomes'
    paginate_by = 20

    def get_queryset(self):
        queryset = Income.objects.filter(user=self.request.user).order_by('-date')
        
        # Date Filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
            
        # Source Filter
        source = self.request.GET.get('source')
        if source:
            queryset = queryset.filter(source__icontains=source)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = {
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'source': self.request.GET.get('source', ''),
        }
        return context

class IncomeCreateView(LoginRequiredMixin, generic.CreateView):
    model = Income
    form_class = IncomeForm
    template_name = 'expenses/income_form.html'
    success_url = reverse_lazy('income-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class IncomeUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Income
    form_class = IncomeForm
    template_name = 'expenses/income_form.html'
    success_url = reverse_lazy('income-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return Income.objects.filter(user=self.request.user)

class IncomeDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Income
    template_name = 'expenses/income_confirm_delete.html'
    success_url = reverse_lazy('income-list')

    def get_queryset(self):
        return Income.objects.filter(user=self.request.user)



class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'expenses/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.now()
        
        # Get year/month from URL or default to current
        year = self.kwargs.get('year', today.year)
        month = self.kwargs.get('month', today.month)
        
        # Validate year/month
        try:
            year = int(year)
            month = int(month)
            if month < 1 or month > 12:
                raise ValueError
        except ValueError:
            year = today.year
            month = today.month

        # Calculate prev/next month for navigation
        if month == 1:
            prev_month_date = date(year - 1, 12, 1)
        else:
            prev_month_date = date(year, month - 1, 1)
            
        if month == 12:
            next_month_date = date(year + 1, 1, 1)
        else:
            next_month_date = date(year, month + 1, 1)

        # Get search query
        search_query = self.request.GET.get('search', '')

        # Base filters
        expense_filters = Q(user=self.request.user, date__year=year, date__month=month)
        income_filters = Q(user=self.request.user, date__year=year, date__month=month)
        
        if search_query:
            # Filter expenses by description or category
            expense_filters &= (Q(description__icontains=search_query) | Q(category__icontains=search_query))
            # Filter income by source or description
            income_filters &= (Q(source__icontains=search_query) | Q(description__icontains=search_query))

        # Get Expense and Income Data for the month
        expenses = Expense.objects.filter(expense_filters).values('date').annotate(total=Sum('amount'))
        
        incomes = Income.objects.filter(income_filters).values('date').annotate(total=Sum('amount'))
        
        # Map data for easy lookup by day
        # Keys are integers (day of month)
        expense_map = {e['date'].day: e['total'] for e in expenses}
        income_map = {i['date'].day: i['total'] for i in incomes}
        
        # Build Calendar Grid
        cal = calendar.Calendar(firstweekday=6) # Start on Sunday
        month_days = cal.monthdayscalendar(year, month)
        
        # Transform into a list of weeks, where each day is an object
        calendar_data = []
        for week in month_days:
            week_data = []
            for day in week:
                if day == 0:
                    week_data.append(None) # Empty slot
                else:
                    week_data.append({
                        'day': day,
                        'income': income_map.get(day, 0),
                        'expense': expense_map.get(day, 0),
                    })
            calendar_data.append(week_data)
        
        context['calendar_data'] = calendar_data
        context['current_year'] = year
        context['current_month'] = month
        context['month_name'] = calendar.month_name[month]
        context['prev_year'] = prev_month_date.year
        context['prev_month'] = prev_month_date.month
        context['next_year'] = next_month_date.year
        context['next_month'] = next_month_date.month
        context['search_query'] = search_query
        
        return context
