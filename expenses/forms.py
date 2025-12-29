from django import forms
from .models import Expense, Category

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['date', 'amount', 'description', 'category']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # If user is provided, populate category choices
        if user:
            categories = Category.objects.filter(user=user).order_by('name')
            # Create choices list: [(name, name), ...]
            choices = [(cat.name, cat.name) for cat in categories]
            self.fields['category'].widget = forms.Select(choices=choices, attrs={'class': 'form-select'})
        else:
            self.fields['category'].widget = forms.TextInput(attrs={'class': 'form-control'})

    def clean_category(self):
        category = self.cleaned_data.get('category')
        if category:
            return category.strip()
        return category
