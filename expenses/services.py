"""
Service classes for shared expense calculations.
"""
from decimal import Decimal
from collections import defaultdict
from django.db.models import Q
from .models import SharedExpense, Share, Friend


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
                    friend_id: {
                        'friend': Friend object,
                        'name': str,
                        'lent': Decimal,      # Amount user lent to this friend
                        'borrowed': Decimal,  # Amount user borrowed from this friend
                        'net': Decimal        # Net balance (lent - borrowed)
                    }
                }
        
        Requirements:
            - 6.1: Calculate lent amounts when user is payer
            - 6.2: Calculate borrowed amounts when user is not payer
            - 6.3: Exclude user's own share from lent calculations
            - 6.5: Calculate net balances (lent - borrowed)
        """
        # Initialize balance tracking dictionary by friend ID
        balances = defaultdict(lambda: {
            'friend': None,
            'name': '',
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
            'expense'
        ).prefetch_related(
            'participants',
            'participants__friend',
            'shares',
            'shares__participant',
            'shares__participant__friend'
        )

        # Process each shared expense
        for shared_expense in shared_expenses:
            # Get the user's participant record for this expense
            user_participant = shared_expense.participants.filter(is_user=True).first()
            
            if not user_participant:
                # Skip if user is not a participant (shouldn't happen, but defensive)
                continue
            
            # Check if user is the payer (using is_payer field directly)
            is_user_payer = user_participant.is_payer

            if is_user_payer:
                # Requirement 6.1: Calculate lent amounts when user is payer
                # Requirement 6.3: Exclude user's own share from lent calculations
                
                # Get all shares for this expense
                for share in shared_expense.shares.all():
                    participant = share.participant
                    
                    # Skip the user's own share
                    if participant.id == user_participant.id:
                        continue
                    
                    # Get the friend for this participant
                    friend = participant.friend
                    if friend:
                        friend_id = friend.id
                        balances[friend_id]['friend'] = friend
                        balances[friend_id]['name'] = friend.name
                        balances[friend_id]['lent'] += share.amount
            else:
                # Requirement 6.2: Calculate borrowed amounts when user is not payer

                # Find the user's share in this expense
                user_share = shared_expense.shares.filter(
                    participant=user_participant
                ).first()
                
                if user_share:
                    # The payer is who the user borrowed from
                    payer = shared_expense.payer
                    if payer and payer.friend:
                        friend = payer.friend
                        friend_id = friend.id
                        balances[friend_id]['friend'] = friend
                        balances[friend_id]['name'] = friend.name
                        balances[friend_id]['borrowed'] += user_share.amount

        # Requirement 6.5: Calculate net balances (lent - borrowed)
        for friend_id in balances:
            lent = balances[friend_id]['lent']
            borrowed = balances[friend_id]['borrowed']
            balances[friend_id]['net'] = lent - borrowed

        # Convert defaultdict to regular dict for cleaner return
        return dict(balances)

    @staticmethod
    def get_friends_summary(user):
        """
        Get all friends with their current balances.

        Args:
            user: The Django User object

        Returns:
            list: List of dicts with friend info and balances, sorted by net balance
        """
        # Get all friends who have participated in user's shared expenses
        friends_in_expenses = Friend.objects.filter(
            expense_participations__shared_expense__expense__user=user
        ).distinct()

        # Calculate balances for all time
        balances = BalanceCalculationService.calculate_balances(user)

        # Build summary list
        friends_summary = []
        for friend in friends_in_expenses:
            balance_data = balances.get(friend.id, {
                'lent': Decimal('0.00'),
                'borrowed': Decimal('0.00'),
                'net': Decimal('0.00')
            })

            friends_summary.append({
                'friend': friend,
                'id': friend.id,
                'name': friend.name,
                'email': friend.email,
                'phone': friend.phone,
                'lent': balance_data['lent'],
                'borrowed': balance_data['borrowed'],
                'net': balance_data['net'],
                'net_abs': abs(balance_data['net']),
                'transactions_count': friend.expense_participations.filter(
                    shared_expense__expense__user=user
                ).count()
            })

        # Sort by absolute net balance (highest first)
        friends_summary.sort(key=lambda x: abs(x['net']), reverse=True)

        return friends_summary

    @staticmethod
    def get_transactions_by_friend(user, start_date=None, end_date=None):
        """
        Get detailed transaction history for each friend.

        Args:
            user: The Django User object
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            dict: Dictionary mapping friend_id to list of transaction details:
                {
                    friend_id: [
                        {
                            'date': date,
                            'description': str,
                            'total_amount': Decimal,
                            'your_share': Decimal,
                            'friend_share': Decimal,
                            'you_paid': bool,
                            'expense_id': int
                        },
                        ...
                    ]
                }
        """
        from collections import defaultdict
        
        transactions_by_friend = defaultdict(list)
        
        # Build query for shared expenses
        query = Q(expense__user=user)
        if start_date:
            query &= Q(expense__date__gte=start_date)
        if end_date:
            query &= Q(expense__date__lte=end_date)
        
        # Get all shared expenses
        shared_expenses = SharedExpense.objects.filter(query).select_related(
            'expense'
        ).prefetch_related(
            'participants',
            'participants__friend',
            'shares',
            'shares__participant',
            'shares__participant__friend'
        ).order_by('-expense__date')
        
        # Process each shared expense
        for shared_expense in shared_expenses:
            expense = shared_expense.expense
            
            # Get user participant
            user_participant = shared_expense.participants.filter(is_user=True).first()
            if not user_participant:
                continue
            
            # Get user's share
            user_share_obj = shared_expense.shares.filter(participant=user_participant).first()
            user_share_amount = user_share_obj.amount if user_share_obj else Decimal('0.00')
            
            # Check if user paid
            you_paid = user_participant.is_payer
            
            # Get all other participants (friends)
            for participant in shared_expense.participants.all():
                if participant.is_user:
                    continue
                
                friend = participant.friend
                if not friend:
                    continue
                
                # Get friend's share
                friend_share_obj = shared_expense.shares.filter(participant=participant).first()
                friend_share_amount = friend_share_obj.amount if friend_share_obj else Decimal('0.00')
                
                # Create transaction record
                transaction = {
                    'date': expense.date,
                    'description': expense.description,
                    'total_amount': expense.amount,
                    'your_share': user_share_amount,
                    'friend_share': friend_share_amount,
                    'you_paid': you_paid,
                    'friend_paid': participant.is_payer,
                    'expense_id': expense.id,
                    'category': expense.category,
                    'payment_method': expense.payment_method
                }
                
                transactions_by_friend[friend.id].append(transaction)
        
        return dict(transactions_by_friend)
