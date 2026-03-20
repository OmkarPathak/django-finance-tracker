import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from ..forms import GoalContributionForm, SavingsGoalForm
from ..models import SavingsGoal


class SavingsGoalListView(LoginRequiredMixin, ListView):
    model = SavingsGoal
    template_name = 'expenses/goal_list.html'
    context_object_name = 'ignored'

    def get_queryset(self):
        return SavingsGoal.objects.filter(user=self.request.user).order_by('created_at', 'id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_goals = list(self.get_queryset())
        profile = self.request.user.profile
        limit = float('inf') if profile.is_pro else (3 if profile.is_plus else 1)
        for i, goal in enumerate(all_goals):
            goal.is_locked = i >= limit
        context.update({'goals': all_goals, 'total_saved': round(sum(g.current_amount for g in all_goals), 2), 'can_create_goal': len(all_goals) < limit})
        return context

class SavingsGoalCreateView(LoginRequiredMixin, CreateView):
    model = SavingsGoal
    form_class = SavingsGoalForm
    template_name = 'expenses/goal_form.html'
    success_url = reverse_lazy('goal-list')
    def dispatch(self, request, *args, **kwargs):
        profile = request.user.profile
        if not profile.is_pro:
            limit = 3 if profile.is_plus else 1
            if SavingsGoal.objects.filter(user=request.user).count() >= limit:
                messages.error(request, _("Goal limit reached."))
                return redirect('goal-list')
        return super().dispatch(request, *args, **kwargs)
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs(); kwargs['user'] = self.request.user
        return kwargs

class SavingsGoalUpdateView(LoginRequiredMixin, UpdateView):
    model = SavingsGoal
    form_class = SavingsGoalForm
    template_name = 'expenses/goal_form.html'
    success_url = reverse_lazy('goal-list')
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object(); profile = request.user.profile
        if not profile.is_pro:
            limit = 3 if profile.is_plus else 1
            goals = list(SavingsGoal.objects.filter(user=request.user).order_by('created_at', 'id'))
            if obj in goals and goals.index(obj) >= limit:
                messages.error(request, _("This goal is locked."))
                return redirect('goal-list')
        return super().dispatch(request, *args, **kwargs)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs(); kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def form_valid(self, form):
        from django.contrib import messages
        from django.utils.translation import gettext as _
        messages.success(self.request, _("Savings goal updated successfully!"))
        return super().form_valid(form)

class SavingsGoalDeleteView(LoginRequiredMixin, DeleteView):
    model = SavingsGoal
    success_url = reverse_lazy('goal-list')
    def get_queryset(self): return SavingsGoal.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        from django.contrib import messages
        from django.utils.translation import gettext as _
        messages.success(self.request, _("Savings goal deleted successfully."))
        return super().delete(request, *args, **kwargs)

class SavingsGoalDetailView(LoginRequiredMixin, View):
    template_name = 'expenses/goal_detail.html'
    def get(self, request, pk):
        goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
        profile = request.user.profile; is_locked = False
        if not profile.is_pro:
             limit = float('inf') if profile.is_pro else (3 if profile.is_plus else 1)
             goals = list(SavingsGoal.objects.filter(user=request.user).order_by('created_at', 'id'))
             is_locked = (goal in goals and goals.index(goal) >= limit)
        return render(request, self.template_name, {'goal': goal, 'is_locked': is_locked, 'contributions': goal.contributions.all().order_by('-date'), 'form': GoalContributionForm()})
    def post(self, request, pk):
        goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
        if request.content_type == 'application/json':
            try:
                if json.loads(request.body).get('clear_confetti'):
                    request.session.pop('trigger_confetti', None)
                    return JsonResponse({'success': True})
            except:
                pass
        # Lock check for POST contributions
        profile = request.user.profile
        if not profile.is_pro:
             limit = 3 if profile.is_plus else 1
             goals = list(SavingsGoal.objects.filter(user=request.user).order_by('created_at', 'id'))
             if goal in goals and goals.index(goal) >= limit:
                 messages.error(request, _("This goal is locked."))
                 return redirect('goal-list')
        form = GoalContributionForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False); c.goal = goal; c.save()
            request.session['trigger_confetti'] = True
            return redirect('goal-detail', pk=goal.pk)
        return render(request, self.template_name, {'goal': goal, 'form': form})
