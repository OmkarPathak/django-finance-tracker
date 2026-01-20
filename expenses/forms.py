from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from allauth.socialaccount.models import SocialAccount
from .models import Expense, Category, Income, RecurringTransaction
import json
from decimal import Decimal

from datetime import date

class ExpenseForm(forms.ModelForm):
    # Add expense type selection field
    expense_type = forms.ChoiceField(
        choices=[('personal', 'Personal Expense'), ('shared', 'Shared Expense')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='personal',
        required=True
    )
    
    # Hidden fields for shared expense data
    participants_json = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    payer_id = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
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
        self.user = user
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
            
            # Only set default participant if this is a new expense (not editing)
            # Check if participants_json already has initial data from the view
            if not self.initial.get('participants_json'):
                # Pre-populate user as first participant in participants_json
                default_participant = {
                    'name': user.username,
                    'is_user': True,
                    'share_amount': ''
                }
                self.fields['participants_json'].initial = json.dumps([default_participant])
        else:
            self.fields['category'].widget = forms.TextInput(attrs={'class': 'form-control'})

    def clean_category(self):
        category = self.cleaned_data.get('category')
        if category:
            return category.strip()
        return category
    
    def clean_participants_json(self):
        """Parse and validate participants JSON data."""
        participants_json = self.cleaned_data.get('participants_json')
        expense_type = self.data.get('expense_type')
        
        # Only validate for shared expenses
        if expense_type != 'shared':
            return participants_json
        
        if not participants_json:
            raise forms.ValidationError('Participants data is required for shared expenses.')
        
        try:
            participants = json.loads(participants_json)
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid participants data format.')
        
        if not isinstance(participants, list):
            raise forms.ValidationError('Participants data must be a list.')
        
        if len(participants) < 2:
            raise forms.ValidationError('Shared expenses require at least 2 participants.')
        
        # Validate each participant
        participant_names = []
        for participant in participants:
            if not isinstance(participant, dict):
                raise forms.ValidationError('Each participant must be an object.')
            
            name = participant.get('name', '').strip()
            if not name:
                raise forms.ValidationError('Participant name cannot be empty.')
            
            # Check for duplicate names
            if name in participant_names:
                raise forms.ValidationError(f'Participant name must be unique within this expense: {name}')
            participant_names.append(name)
            
            # Validate share amount if provided
            share_amount = participant.get('share_amount')
            if share_amount is not None and share_amount != '':
                try:
                    share_decimal = Decimal(str(share_amount))
                    if share_decimal <= 0:
                        raise forms.ValidationError(f'Share amount must be positive for {name}.')
                except (ValueError, TypeError):
                    raise forms.ValidationError(f'Invalid share amount for {name}.')
        
        return participants_json
    
    def clean_payer_id(self):
        """Validate payer_id field."""
        payer_id = self.cleaned_data.get('payer_id')
        expense_type = self.data.get('expense_type')
        
        # Only validate for shared expenses
        if expense_type != 'shared':
            return payer_id
        
        if not payer_id:
            raise forms.ValidationError('Payer selection is required for shared expenses.')
        
        return payer_id
    
    def clean(self):
        cleaned_data = super().clean()
        has_cashback = cleaned_data.get('has_cashback')
        cashback_type = cleaned_data.get('cashback_type')
        cashback_value = cleaned_data.get('cashback_value')
        expense_type = self.data.get('expense_type')
        
        # If cashback is enabled, validate type and value
        if has_cashback:
            if not cashback_type:
                self.add_error('cashback_type', 'Please select a cashback type.')
            if not cashback_value or cashback_value <= 0:
                self.add_error('cashback_value', 'Please enter a valid cashback value.')
        
        # Validate shared expense specific fields
        if expense_type == 'shared':
            participants_json = cleaned_data.get('participants_json')
            payer_id = cleaned_data.get('payer_id')
            amount = cleaned_data.get('amount')
            
            if participants_json and amount:
                try:
                    participants = json.loads(participants_json)
                    
                    # Validate share sum equals total amount
                    total_shares = Decimal('0')
                    payer_found = False
                    
                    for participant in participants:
                        share_amount = participant.get('share_amount')
                        if share_amount is not None and share_amount != '':
                            total_shares += Decimal(str(share_amount))
                        
                        # Check if payer is in participants list
                        if payer_id and participant.get('name') == payer_id:
                            payer_found = True
                    
                    # Validate share sum equals total
                    if total_shares > 0 and total_shares != amount:
                        difference = abs(amount - total_shares)
                        self.add_error(
                            None, 
                            f'Share amounts must sum to total expense amount. Difference: ₹{difference}'
                        )
                    
                    # Validate payer is a participant
                    if payer_id and not payer_found:
                        self.add_error('payer_id', 'Payer must be one of the participants.')
                
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    self.add_error(None, f'Error validating shared expense data: {str(e)}')
        
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
