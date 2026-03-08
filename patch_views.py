import ast
import traceback

def get_class_end(filepath, class_name):
    with open(filepath, 'r') as f:
        content = f.read()
    tree = ast.parse(content)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node.end_lineno
    return None

def inject(filepath, class_name, code):
    end_lineno = get_class_end(filepath, class_name)
    if not end_lineno:
        print(f"Class {class_name} not found in {filepath}")
        return
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Needs to match class indentation + method indentation
    lines.insert(end_lineno, '\n' + code + '\n')
    with open(filepath, 'w') as f:
        f.writelines(lines)
    print(f"Patched {class_name} in {filepath}")

# Mapping of missing methods to their code and destination files
patches = [
    # expenses.py
    {
        'file': 'expenses/views/expenses.py',
        'class': 'ExpenseUpdateView',
        'code': '''    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = self.request.POST.get('next') or self.request.GET.get('next') or ''
        
        # Get top 5 frequent categories for this user
        frequent_categories = Expense.objects.filter(user=self.request.user).values('category').annotate(count=Count('category')).order_by('-count')[:5]
        context['frequent_categories'] = [item['category'] for item in frequent_categories]
        
        return context'''
    },
    # categories.py
    {
        'file': 'expenses/views/categories.py',
        'class': 'CategoryCreateView',
        'code': '''    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from ..models import BOOTSTRAP_ICONS
        context['bootstrap_icons'] = BOOTSTRAP_ICONS
        # Check Limits
        current_count = Category.objects.filter(user=self.request.user).count()
        limit = 5 # Free
        if self.request.user.profile.is_plus:
            limit = 10
        if self.request.user.profile.is_pro:
            limit = float('inf')

        context['reached_limit'] = current_count >= limit
        context['category_limit'] = limit
        return context'''
    },
    {
        'file': 'expenses/views/categories.py',
        'class': 'CategoryUpdateView',
        'code': '''    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from ..models import BOOTSTRAP_ICONS
        context['bootstrap_icons'] = BOOTSTRAP_ICONS
        context['next_url'] = self.request.POST.get('next') or self.request.GET.get('next') or ''
        return context

    def form_valid(self, form):
        from django.db import IntegrityError
        from django.contrib import messages
        try:
            # Store old name to update related expenses
            old_name = self.get_object().name
            response = super().form_valid(form)
            new_name = self.object.name
            
            if old_name != new_name:
                from ..models import Expense
                Expense.objects.filter(user=self.request.user, category=old_name).update(category=new_name)
                
            return response
        except IntegrityError:
            messages.error(self.request, "This category already exists.")
            return self.form_invalid(form)'''
    },
    # income.py
    {
        'file': 'expenses/views/income.py',
        'class': 'IncomeListView',
        'code': '''    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from ..models import CURRENCY_CHOICES
        from django.db.models import Sum
        context['currency_choices'] = CURRENCY_CHOICES
        
        # Calculate stats for the filtered queryset
        filtered_queryset = getattr(self, 'object_list', self.get_queryset())
        context['filtered_count'] = filtered_queryset.count()
        context['filtered_amount'] = filtered_queryset.aggregate(Sum('base_amount'))['base_amount__sum'] or 0
        
        context['filter_form'] = {
            'date_from': getattr(self, 'date_from', ''),
            'date_to': getattr(self, 'date_to', ''),
            'source': self.request.GET.get('source', ''),
        }
        return context'''
    },
    {
        'file': 'expenses/views/income.py',
        'class': 'IncomeCreateView',
        'code': '''    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = self.request.POST.get('next') or self.request.GET.get('next') or ''
        return context'''
    },
    {
        'file': 'expenses/views/income.py',
        'class': 'IncomeUpdateView',
        'code': '''    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = self.request.POST.get('next') or self.request.GET.get('next') or ''
        return context

    def form_valid(self, form):
        from django.db import IntegrityError
        from django.contrib import messages
        from django.utils.translation import gettext as _
        try:
            return super().form_valid(form)
        except IntegrityError:
            messages.error(self.request, _("This income entry already exists."))
            return self.form_invalid(form)'''
    },
    # recurring.py
    {
        'file': 'expenses/views/recurring.py',
        'class': 'RecurringTransactionCreateView',
        'code': '''    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = self.request.POST.get('next') or self.request.GET.get('next') or ''
        return context'''
    },
    {
        'file': 'expenses/views/recurring.py',
        'class': 'RecurringTransactionUpdateView',
        'code': '''    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = self.request.POST.get('next') or self.request.GET.get('next') or ''
        return context

    def get_queryset(self):
        # We need to import RecurringTransaction if not already in scope, but it's in models.
        # This view already defines model=RecurringTransaction, so it's in scope.
        return super().get_queryset().filter(user=self.request.user)'''
    },
    {
        'file': 'expenses/views/recurring.py',
        'class': 'RecurringTransactionDeleteView',
        'code': '''    def form_valid(self, form):
        # Calculate savings
        from django.utils.translation import gettext as _
        from django.contrib import messages
        obj = self.object
        amount = obj.amount
        if obj.frequency == 'DAILY':
            yearly_saving = amount * 365
        elif obj.frequency == 'WEEKLY':
            yearly_saving = amount * 52
        elif obj.frequency == 'MONTHLY':
            yearly_saving = amount * 12
        else: # YEARLY
            yearly_saving = amount
            
        currency = '\u20b9'
        if hasattr(self.request.user, 'userprofile'):
            currency = self.request.user.userprofile.currency
            
        messages.success(self.request, _("You just saved %(currency)s%(amount)s/year 🎉") % {'currency': currency, 'amount': f"{yearly_saving:,.0f}"})
        return super().form_valid(form)'''
    },
    # misc.py (ContactView)
    {
        'file': 'expenses/views/misc.py',
        'class': 'ContactView',
        'code': '''    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _check_rate_limit(self, ip):
        from django.core.cache import cache
        hourly_key = f'contact_hourly_{ip}'
        daily_key = f'contact_daily_{ip}'
        
        hourly_count = cache.get(hourly_key, 0)
        daily_count = cache.get(daily_key, 0)
        
        if hourly_count >= getattr(self, 'RATE_LIMIT_HOURLY', 5):
            return False, "Too many submissions. Please try again in an hour."
        
        if daily_count >= getattr(self, 'RATE_LIMIT_DAILY', 20):
            return False, "Daily submission limit reached. Please try again tomorrow."
        
        cache.set(hourly_key, hourly_count + 1, 3600)  # 1 hour
        cache.set(daily_key, daily_count + 1, 86400)   # 24 hours
        
        return True, None

    def _is_spam_content(self, text):
        text_lower = text.lower()
        if 'http://' in text_lower or 'https://' in text_lower or 'www.' in text_lower:
            return True, "Messages with URLs are not allowed."
        
        spam_keywords = getattr(self, 'SPAM_KEYWORDS', ['seo', 'marketing', 'guarantee', 'crypto', 'bitcoin'])
        for keyword in spam_keywords:
            if keyword in text_lower:
                return True, "Your message was flagged as potential spam."
        
        if len(text) > 20:
            caps_count = sum(1 for c in text if c.isupper())
            if caps_count / len(text) > 0.5:
                return True, "Please don't use excessive capitalization."
        
        if len(text.strip()) < getattr(self, 'MIN_MESSAGE_LENGTH', 10):
            return True, "Please provide a more detailed message."
        
        return False, None

    def _is_disposable_email(self, email):
        domain = email.split('@')[-1].lower()
        return domain in getattr(self, 'DISPOSABLE_DOMAINS', ['mailinator.com', '10minutemail.com', 'tempmail.com'])'''
    },
    # goals.py
    {
        'file': 'expenses/views/goals.py',
        'class': 'SavingsGoalUpdateView',
        'code': '''    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def form_valid(self, form):
        from django.utils.translation import gettext as _
        from django.contrib import messages
        messages.success(self.request, _("Savings goal updated successfully!"))
        return super().form_valid(form)'''
    },
    {
        'file': 'expenses/views/goals.py',
        'class': 'SavingsGoalDeleteView',
        'code': '''    def delete(self, request, *args, **kwargs):
        from django.utils.translation import gettext as _
        from django.contrib import messages
        messages.success(self.request, _("Savings goal deleted successfully."))
        return super().delete(request, *args, **kwargs)'''
    },
    # dashboard.py
    {
        'file': 'expenses/views/dashboard.py',
        'class': 'YearInReviewView',
        'code': '''    def dispatch(self, request, *args, **kwargs):
        from django.contrib import messages
        from django.shortcuts import redirect
        if not request.user.profile.is_plus:
            messages.info(request, "Year in Review is a Premium feature. Upgrade to Plus or Pro to unlock your personalized financial story!")
            return redirect('pricing')
        return super().dispatch(request, *args, **kwargs)'''
    }
]

for p in patches:
    try:
        inject(p['file'], p['class'], p['code'])
    except Exception as e:
        print(f"Error patching {p['class']}: {e}")
        traceback.print_exc()

