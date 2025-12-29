from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import modelformset_factory
from .forms import ExpenseForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views import generic
from django.db.models import Sum, Q
from django.views import generic
from django.db.models import Sum, Q
from .models import Expense, Category
import pandas as pd
import pandas as pd
from datetime import datetime
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
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')
    selected_category = request.GET.get('category')
    
    if selected_year is None:
        selected_year = datetime.now().year
    if selected_month is None:
        selected_month = datetime.now().month
    
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
    # Define a color palette
    colors = ['#38bdf8', '#818cf8', '#c084fc', '#f472b6', '#fb7185', '#22d3ee', '#34d399', '#fbfb8c']
    
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
    
    context = {
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
        search_query = self.request.GET.get('search')
        
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
        year_param = self.request.GET.get('year')
        if year_param is None:
            context['selected_year'] = datetime.now().year
        elif year_param:
            try:
                context['selected_year'] = int(year_param)
            except ValueError:
                context['selected_year'] = None
        else:
            context['selected_year'] = None
            
        return context

class ExpenseCreateView(generic.TemplateView):
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

class ExpenseUpdateView(generic.UpdateView):
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

class ExpenseDeleteView(generic.DeleteView):
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expense-list')

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)
    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

class CategoryListView(generic.ListView):
    model = Category
    template_name = 'expenses/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).order_by('name')

class CategoryCreateView(generic.CreateView):
    model = Category
    fields = ['name', 'limit']
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('category-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class CategoryUpdateView(generic.UpdateView):
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

class CategoryDeleteView(generic.DeleteView):
    model = Category
    template_name = 'expenses/category_confirm_delete.html'
    success_url = reverse_lazy('category-list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
