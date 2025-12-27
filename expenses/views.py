from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views import generic
from django.db.models import Sum
from .models import Expense
import pandas as pd
from datetime import datetime

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
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')
    selected_category = request.GET.get('category')
    
    if selected_year:
        expenses = expenses.filter(date__year=selected_year)
    if selected_month:
        expenses = expenses.filter(date__month=selected_month)
    if selected_category:
        expenses = expenses.filter(category=selected_category)
        
    # Get filters
    all_dates = Expense.objects.filter(user=request.user).dates('date', 'year', order='DESC')
    years = [d.year for d in all_dates]
    all_categories = Expense.objects.filter(user=request.user).values_list('category', flat=True).distinct().order_by('category')

    # 1. Category Chart Data (Distribution)
    category_data = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    categories = [item['category'] for item in category_data]
    category_amounts = [float(item['total']) for item in category_data]
    
    # 2. Time Trend (Stacked) Data
    from django.db.models.functions import TruncMonth, TruncDay
    
    # Determine Labels (X-Axis)
    if selected_month and selected_year:
        # Daily view
        trend_qs = expenses.annotate(period=TruncDay('date'))
        date_format = '%d %b'
        trend_title = f"Daily Expenses for {selected_month}/{selected_year}"
    else:
        # Monthly view
        trend_qs = expenses.annotate(period=TruncMonth('date'))
        date_format = '%b %Y'
        trend_title = "Monthly Expenses Trend"

    # Aggregate by Period AND Category for Stacking
    stacked_data = trend_qs.values('period', 'category').annotate(total=Sum('amount')).order_by('period')
    
    # Process into Chart.js Datasets
    # 1. Get unique sorted periods
    periods = sorted(list(set(item['period'] for item in stacked_data)))
    trend_labels = [p.strftime(date_format) for p in periods]
    
    # 2. Build datasets map: { 'CategoryA': [0, 10, 0...], 'CategoryB': ... }
    # Initialize with zeros
    dataset_map = { cat: [0] * len(periods) for cat in all_categories }
    
    for item in stacked_data:
        p_idx = periods.index(item['period'])
        cat = item['category']
        if cat in dataset_map:
            dataset_map[cat][p_idx] = float(item['total'])
            
    # 3. Convert map to list of dataset objects for Chart.js
    trend_datasets = []
    # Define a color palette
    colors = ['#38bdf8', '#818cf8', '#c084fc', '#f472b6', '#fb7185', '#22d3ee', '#34d399', '#fbfb8c']
    
    for i, (cat, data) in enumerate(dataset_map.items()):
        # If a category is selected, filtering already happened, but we still use this logic
        # If user filters by 'Food', only 'Food' key will have data, others 0 (or empty query).
        # Optimization: Only include categories that have non-zero total in the current view?
        # For stacked, it's nice to keep consistent colors.
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
    
    context = {
        'recent_transactions': expenses.order_by('-date')[:5],
        'categories': categories,
        'category_amounts': category_amounts,
        'category_data': category_data, # Passing full queryset for the summary table
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
        'months_list': range(1, 13),
        'total_expenses': total_expenses,
        'transaction_count': transaction_count,
        'top_category': top_category,
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

class ExpenseListView(generic.ListView):
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
        
        if year:
            queryset = queryset.filter(date__year=year)
        if month:
            queryset = queryset.filter(date__month=month)
        if category:
            queryset = queryset.filter(category=category)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get unique years and categories for validation
        user_expenses = Expense.objects.filter(user=self.request.user)
        years = user_expenses.dates('date', 'year', order='DESC')
        categories = user_expenses.values_list('category', flat=True).distinct().order_by('category')
        
        context['years'] = years
        context['categories'] = categories
        context['months_list'] = range(1, 13)
        return context

class ExpenseCreateView(generic.CreateView):
    model = Expense
    fields = ['date', 'amount', 'description', 'category']
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expense-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class ExpenseUpdateView(generic.UpdateView):
    model = Expense
    fields = ['date', 'amount', 'description', 'category']
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expense-list')

    def get_queryset(self):
        # Ensure user can only edit their own expenses
        return Expense.objects.filter(user=self.request.user)

class ExpenseDeleteView(generic.DeleteView):
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expense-list')

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)
