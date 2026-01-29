from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Friend
from django import forms


class FriendForm(forms.ModelForm):
    """Form for creating and editing friends."""
    
    class Meta:
        model = Friend
        fields = ['name', 'email', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Friend name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'}),
        }
        help_texts = {
            'name': 'Required. This name will appear in shared expenses.',
            'email': 'Optional. Email address for notifications.',
            'phone': 'Optional. Phone number for contact.',
        }


class FriendListView(LoginRequiredMixin, generic.ListView):
    """View to list all friends."""
    model = Friend
    template_name = 'expenses/friend_list.html'
    context_object_name = 'friends'
    
    def get_queryset(self):
        return Friend.objects.all().order_by('name')


class FriendCreateView(LoginRequiredMixin, generic.CreateView):
    """View to create a new friend."""
    model = Friend
    form_class = FriendForm
    template_name = 'expenses/friend_form.html'
    success_url = reverse_lazy('friend-list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Friend "{form.instance.name}" added successfully!')
        return super().form_valid(form)


class FriendUpdateView(LoginRequiredMixin, generic.UpdateView):
    """View to update an existing friend."""
    model = Friend
    form_class = FriendForm
    template_name = 'expenses/friend_form.html'
    success_url = reverse_lazy('friend-list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Friend "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class FriendDeleteView(LoginRequiredMixin, generic.DeleteView):
    """View to delete a friend."""
    model = Friend
    template_name = 'expenses/friend_confirm_delete.html'
    success_url = reverse_lazy('friend-list')
    
    def delete(self, request, *args, **kwargs):
        friend_name = self.get_object().name
        messages.success(request, f'Friend "{friend_name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)
