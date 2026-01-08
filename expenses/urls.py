from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('', views.LandingPageView.as_view(), name='landing'),
    path('dashboard/', views.home_view, name='home'),
    path('budget/', views.BudgetDashboardView.as_view(), name='budget'),
    path('upload/', views.upload_view, name='upload'),
    path('export/', views.export_expenses, name='export-expenses'),
    path('expenses/', views.ExpenseListView.as_view(), name='expense-list'),
    path('expenses/add/', views.ExpenseCreateView.as_view(), name='expense-create'),
    path('expenses/<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense-edit'),
    path('expenses/<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense-delete'),
    path('category/create/ajax/', views.create_category_ajax, name='category-create-ajax'),
    path('category/list/', views.CategoryListView.as_view(), name='category-list'),
    path('category/add/', views.CategoryCreateView.as_view(), name='category-create'),
    path('category/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category-edit'),
    path('category/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category-delete'),
    
    # Income
    path('income/list/', views.IncomeListView.as_view(), name='income-list'),
    path('income/add/', views.IncomeCreateView.as_view(), name='income-create'),
    path('income/<int:pk>/edit/', views.IncomeUpdateView.as_view(), name='income-edit'),
    path('income/<int:pk>/delete/', views.IncomeDeleteView.as_view(), name='income-delete'),

    # Calendar
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('calendar/<int:year>/<int:month>/', views.CalendarView.as_view(), name='calendar-month'),
    # Recurring Transactions
    path('recurring/', views.RecurringTransactionListView.as_view(), name='recurring-list'),
    path('recurring/create/', views.RecurringTransactionCreateView.as_view(), name='recurring-create'),
    path('recurring/<int:pk>/edit/', views.RecurringTransactionUpdateView.as_view(), name='recurring-edit'),
    path('recurring/<int:pk>/delete/', views.RecurringTransactionDeleteView.as_view(), name='recurring-delete'),
    path('settings/currency/', views.CurrencyUpdateView.as_view(), name='currency-settings'),
    path('settings/profile/', views.ProfileUpdateView.as_view(), name='profile-settings'),
    path('account/delete/', views.AccountDeleteView.as_view(), name='account-delete'),
    path('tutorial/complete/', views.complete_tutorial, name='complete-tutorial'),
    
    # Static Pages
    path('privacy-policy/', TemplateView.as_view(template_name='privacy_policy.html'), name='privacy-policy'),
    path('terms-of-service/', TemplateView.as_view(template_name='terms_of_service.html'), name='terms-of-service'),
    path('contact/', TemplateView.as_view(template_name='contact.html'), name='contact'),
]
