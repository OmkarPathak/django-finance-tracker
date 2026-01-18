"""
Service classes for shared expense calculations.
"""
from decimal import Decimal
from collections import defaultdict
from django.db.models import Q
from .models import SharedExpense, Participant, Share


class BalanceCalculationService:
    """
    Service for calculating lent, borrowed, and net balances for shared expenses.
    
    This service handles the core logic for determining:
    - How much a user has lent to each participant (when user is payer)
    - How much a user has borrowed from each participant (when user is not payer)
    - Net balances (lent - borrowed) per participant
    """
    
    @staticmethod
    def calculate_balances(user, start_date=None, end_date=None):
        """
        Calculate lent, borrowed, and net balances per participant for a user.
        
        Args:
            user: The Django User object to calculate balances for
            start_date: Optional start date for filtering expenses (inclusive)
            end_date: Optional end date for filtering expenses (inclusive)
        
        Returns:
            dict: Dictionary mapping participant names to their balance details:
                {
                    'participant_name': {
                        'lent': Decimal,      # Amount user lent to this participant
                        'borrowed': Decimal,  # Amount user borrowed from this participant
                        'net': Decimal        # Net balance (lent - borrowed)
                    }
                }
        
        Requirements:
            - 6.1: Calculate lent amounts when user is payer
            - 6.2: Calculate borrowed amounts when user is not payer
            - 6.3: Exclude user's own share from lent calculations
            - 6.5: Calculate net balances (lent - borrowed)
        """
        # Initialize balance tracking dictionary
        balances = defaultdict(lambda: {
            'lent': Decimal('0.00'),
            'borrowed': Decimal('0.00'),
            'net': Decimal('0.00')
        })
        
        # Build query for shared expenses involving the user
        query = Q(expense__user=user)
        
        # Apply date range filters if provided
        if start_date:
            query &= Q(expense__date__gte=start_date)
        if end_date:
            query &= Q(expense__date__lte=end_date)
        
        # Get all shared expenses for the user within the date range
        shared_expenses = SharedExpense.objects.filter(query).select_related(
            'expense', 'payer'
        ).prefetch_related('participants', 'shares')
        
        # Process each shared expense
        for shared_expense in shared_expenses:
            # Get the user's participant record for this expense
            user_participant = shared_expense.participants.filter(is_user=True).first()
            
            if not user_participant:
                # Skip if user is not a participant (shouldn't happen, but defensive)
                continue
            
            # Check if user is the payer
            is_user_payer = (shared_expense.payer.id == user_participant.id)
            
            if is_user_payer:
                # Requirement 6.1: Calculate lent amounts when user is payer
                # Requirement 6.3: Exclude user's own share from lent calculations
                
                # Get all shares for this expense
                for share in shared_expense.shares.all():
                    participant = share.participant
                    
                    # Skip the user's own share
                    if participant.id == user_participant.id:
                        continue
                    
                    # Add to lent amount for this participant
                    balances[participant.name]['lent'] += share.amount
            else:
                # Requirement 6.2: Calculate borrowed amounts when user is not payer
                
                # Find the user's share in this expense
                user_share = shared_expense.shares.filter(
                    participant=user_participant
                ).first()
                
                if user_share:
                    # The payer's name is who the user borrowed from
                    payer_name = shared_expense.payer.name
                    
                    # Add to borrowed amount from the payer
                    balances[payer_name]['borrowed'] += user_share.amount
        
        # Requirement 6.5: Calculate net balances (lent - borrowed)
        for participant_name in balances:
            lent = balances[participant_name]['lent']
            borrowed = balances[participant_name]['borrowed']
            balances[participant_name]['net'] = lent - borrowed
        
        # Convert defaultdict to regular dict for cleaner return
        return dict(balances)
