from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import JsonResponse

from ..models import Category
from ..forms import CategoryForm

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'expenses/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10

    def get_queryset(self):
        queryset = Category.objects.filter(user=self.request.user).order_by('name')
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        
        # Nudge context for upgrade banner
        profile = self.request.user.profile
        if not profile.is_pro:
            total_categories = Category.objects.filter(user=self.request.user).count()
            if profile.is_plus:
                limit = 10
                upgrade_tier = 'PRO'
            else:
                limit = 5
                upgrade_tier = 'PLUS'
            context['reached_limit'] = total_categories >= limit
            context['current_count'] = total_categories
            context['limit'] = limit
            context['nudge_current'] = total_categories
            context['nudge_limit'] = limit
            context['nudge_feature_name'] = 'categories'
            context['nudge_upgrade_tier'] = upgrade_tier
            context['nudge_at_limit'] = total_categories >= limit
        
        from ..utils import BOOTSTRAP_ICONS
        context['bootstrap_icons'] = BOOTSTRAP_ICONS
        return context

@login_required
def create_category_ajax(request):
    import json
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            if not name:
                return JsonResponse({'success': False, 'error': _('Name is required.')})
                
            profile = request.user.profile
            limit = float('inf') if profile.is_pro else (10 if profile.is_plus else 5)
            if Category.objects.filter(user=request.user).count() >= limit:
                return JsonResponse({'success': False, 'error': _('Category limit reached.')}, status=403)
                
            category = Category.objects.create(user=request.user, name=name)
            return JsonResponse({'success': True, 'id': category.id, 'name': category.name})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False}, status=405)

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('category-list')

    def form_valid(self, form):
        profile = self.request.user.profile
        limit = float('inf') if profile.is_pro else (10 if profile.is_plus else 5)
        if Category.objects.filter(user=self.request.user).count() >= limit:
            messages.error(self.request, _("Category limit reached. Please upgrade."))
            return redirect('pricing')
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from ..utils import BOOTSTRAP_ICONS
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
        return context

class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('category-list')

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        profile = request.user.profile
        limit = float('inf') if profile.is_pro else (10 if profile.is_plus else 5)
        categories = list(Category.objects.filter(user=request.user).order_by('id'))
        if obj in categories and categories.index(obj) >= limit:
            messages.error(request, _("This category is locked."))
            return redirect('category-list')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from ..utils import BOOTSTRAP_ICONS
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
            return self.form_invalid(form)

class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    success_url = reverse_lazy('category-list')
    def get_queryset(self): return Category.objects.filter(user=self.request.user)
