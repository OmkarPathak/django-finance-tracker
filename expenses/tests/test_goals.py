from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from expenses.models import SavingsGoal, GoalContribution, UserProfile
from expenses.forms import SavingsGoalForm, GoalContributionForm

class SavingsGoalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.goal = SavingsGoal.objects.create(
            user=self.user,
            name='Test Goal',
            target_amount=Decimal('1000.00'),
        )

    def test_savings_goal_model_progress(self):
        self.assertEqual(self.goal.progress_percentage, 0)
        self.assertFalse(self.goal.is_completed)
        
        self.goal.current_amount = Decimal('500.00')
        self.goal.save()
        self.assertEqual(self.goal.progress_percentage, 50.0)
        self.assertFalse(self.goal.is_completed)

        self.goal.current_amount = Decimal('1000.00')
        self.goal.save()
        self.assertEqual(self.goal.progress_percentage, 100.0)
        self.assertTrue(self.goal.is_completed)
        
        self.goal.current_amount = Decimal('1500.00')
        self.goal.save()
        self.assertEqual(self.goal.progress_percentage, 100.0)
        self.assertTrue(self.goal.is_completed)

    def test_goal_contribution_updates_goal(self):
        self.assertEqual(self.goal.current_amount, Decimal('0.00'))
        
        contrib1 = GoalContribution.objects.create(goal=self.goal, amount=Decimal('200.00'))
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.current_amount, Decimal('200.00'))
        
        contrib2 = GoalContribution.objects.create(goal=self.goal, amount=Decimal('300.00'))
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.current_amount, Decimal('500.00'))
        
        contrib1.delete()
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.current_amount, Decimal('300.00'))

    def test_savings_goal_form_validation(self):
        form = SavingsGoalForm(data={
            'name': 'Vacation',
            'target_amount': '500.00',
            'currency': '₹',
            'icon': '✈️',
            'color': 'primary'
        })
        self.assertTrue(form.is_valid())
        
        form_invalid = SavingsGoalForm(data={
            'name': 'Vacation',
            'target_amount': '-500.00',
            'currency': '₹',
            'icon': '✈️',
            'color': 'primary'
        })
        self.assertFalse(form_invalid.is_valid())
        self.assertIn('target_amount', form_invalid.errors)

    def test_goal_list_view_free_tier(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('goal-list'))
        self.assertEqual(response.status_code, 200)
        
        # Free user already has 1 goal (from setUp), so can_create_goal should be False
        self.assertFalse(response.context['can_create_goal'])
        self.assertEqual(response.context['total_saved'], Decimal('0.00'))

    def test_goal_list_view_pro_tier(self):
        pro_user = User.objects.create_user(username='prouser', password='testpassword')
        pro_user.profile.tier = 'PRO'
        pro_user.profile.is_lifetime = True
        pro_user.profile.save()
        
        self.client.login(username='prouser', password='testpassword')
        # We need to give pro_user a goal to truly test the limit check
        SavingsGoal.objects.create(user=pro_user, name='Pro Goal 1', target_amount=Decimal('100.00'))
        
        response = self.client.get(reverse('goal-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['can_create_goal'])

    def test_goal_create_limit_for_free_user(self):
        self.client.login(username='testuser', password='testpassword')
        # Trying to load the create page should redirect with a message
        response = self.client.get(reverse('goal-create'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('goal-list'))
        
        # POSTing should also fail
        response = self.client.post(reverse('goal-create'), data={
            'name': 'Second Goal',
            'target_amount': '500.00',
            'currency': '₹',
            'icon': '🚗',
            'color': 'primary'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SavingsGoal.objects.filter(user=self.user).count(), 1)
        
    def test_goal_list_view_plus_tier_limit(self):
        plus_user = User.objects.create_user(username='plususer', password='testpassword')
        plus_user.profile.tier = 'PLUS'
        plus_user.profile.is_lifetime = True
        plus_user.profile.save()
        
        self.client.login(username='plususer', password='testpassword')
        SavingsGoal.objects.create(user=plus_user, name='Plus Goal 1', target_amount=Decimal('100.00'))
        SavingsGoal.objects.create(user=plus_user, name='Plus Goal 2', target_amount=Decimal('100.00'))
        SavingsGoal.objects.create(user=plus_user, name='Plus Goal 3', target_amount=Decimal('100.00'))
        
        response = self.client.get(reverse('goal-list'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['can_create_goal'])
        
    def test_goal_create_limit_for_plus_user(self):
        plus_user = User.objects.create_user(username='plususer2', password='testpassword')
        plus_user.profile.tier = 'PLUS'
        plus_user.profile.is_lifetime = True
        plus_user.profile.save()
        
        self.client.login(username='plususer2', password='testpassword')
        SavingsGoal.objects.create(user=plus_user, name='Plus Goal 1', target_amount=Decimal('100.00'))
        SavingsGoal.objects.create(user=plus_user, name='Plus Goal 2', target_amount=Decimal('100.00'))
        SavingsGoal.objects.create(user=plus_user, name='Plus Goal 3', target_amount=Decimal('100.00'))

        # Trying to load the create page should redirect with a message
        response = self.client.get(reverse('goal-create'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('goal-list'))

    def test_goal_detail_add_funds(self):
        self.client.login(username='testuser', password='testpassword')
        
        response = self.client.post(reverse('goal-detail', kwargs={'pk': self.goal.pk}), data={
            'amount': '250.00',
            'date': '2023-10-01'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('goal-detail', kwargs={'pk': self.goal.pk}))
        
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.current_amount, Decimal('250.00'))
        self.assertEqual(self.goal.contributions.count(), 1)
        self.assertEqual(self.goal.contributions.first().amount, Decimal('250.00'))

    def test_goal_detail_clear_confetti_ajax(self):
        self.client.login(username='testuser', password='testpassword')
        session = self.client.session
        session['trigger_confetti'] = True
        session.save()
        
        response = self.client.post(reverse('goal-detail', kwargs={'pk': self.goal.pk}), 
                               data='{"clear_confetti": true}', 
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('trigger_confetti', self.client.session)
