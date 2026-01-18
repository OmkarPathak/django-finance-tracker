from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from allauth.socialaccount.models import SocialAccount
from .models import Expense, Category, Income, RecurringTransaction

from datetime import date

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['date', 'amount', 'description', 'category', 'payment_method', 'has_cashback', 'cashback_type', 'cashback_value']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'has_cashback': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'cashback_type': forms.Select(attrs={'class': 'form-select'}),
            'cashback_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = date.today
        
        # Make cashback fields optional
        self.fields['has_cashback'].required = False
        self.fields['cashback_type'].required = False
        self.fields['cashback_value'].required = False
        
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
    
    def clean(self):
        cleaned_data = super().clean()
        has_cashback = cleaned_data.get('has_cashback')
        cashback_type = cleaned_data.get('cashback_type')
        cashback_value = cleaned_data.get('cashback_value')
        
        # If cashback is enabled, validate type and value
        if has_cashback:
            if not cashback_type:
                self.add_error('cashback_type', 'Please select a cashback type.')
            if not cashback_value or cashback_value <= 0:
                self.add_error('cashback_value', 'Please enter a valid cashback value.')
        
        return cleaned_data

class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['date', 'amount', 'source', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Salary, Freelance'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = date.today
        
    def clean_source(self):
        source = self.cleaned_data.get('source')
        if source:
            return source.strip()
        return source

class RecurringTransactionForm(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = ['transaction_type', 'amount', 'category', 'source', 'frequency', 'start_date', 'description', 'is_active', 'payment_method']
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-select', 'onchange': 'toggleFields()'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Salary, Rent'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Category field as Select for Expenses
        if user:
            categories = Category.objects.filter(user=user).order_by('name')
            category_choices = [('', '---------')] + [(cat.name, cat.name) for cat in categories]
            self.fields['category'].widget = forms.Select(choices=category_choices, attrs={'class': 'form-select'})
        else:
            self.fields['category'].widget = forms.TextInput(attrs={'class': 'form-control'})
        
        self.fields['source'].widget = forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Salary (For Income only)'})
        
        # Ensure fields are optional at form level since we handle them in clean()
        self.fields['category'].required = False
        self.fields['source'].required = False

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        category = cleaned_data.get('category')
        source = cleaned_data.get('source')

        if transaction_type == 'EXPENSE' and not category:
            self.add_error('category', 'Category is required for expenses.')
        

        if transaction_type == 'INCOME' and not source:
            self.add_error('source', 'Source is required for income.')

        return cleaned_data

class ProfileUpdateForm(forms.ModelForm):
    auth_email = forms.EmailField(required=True, label='Email Address')
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['auth_email'].initial = self.instance.email
        self.fields['auth_email'].initial = self.instance.email
        self.fields['auth_email'].widget.attrs.update({'class': 'form-control'})

        # Check if user has social account
        if SocialAccount.objects.filter(user=self.instance).exists():
            for field in ['first_name', 'last_name', 'auth_email']:
                self.fields[field].disabled = True
                self.fields[field].widget.attrs['disabled'] = 'disabled'
                self.fields[field].required = False
            self.fields['auth_email'].help_text = "Managed by social login. You cannot change this info."

    def clean_auth_email(self):
        email = self.cleaned_data.get('auth_email')
        
        # If the email hasn't changed, allow it (even if duplicates exist in DB)
        if email == self.instance.email:
            return email
            
        if User.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("Email already assigned to another account.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['auth_email']
        if commit:
            user.save()
        return user

class CustomSignupForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email Address')

    class Meta:
        model = User
        fields = ('username', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
