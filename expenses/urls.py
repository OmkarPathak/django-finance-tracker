from django.urls import path
from django.views.generic import TemplateView

from . import views, views_payment, views_accounts, views_creditcards, views_friends

urlpatterns = [
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("", views.LandingPageView.as_view(), name="landing"),
    path("dashboard/", views.home_view, name="home"),
    path("budget/", views.BudgetDashboardView.as_view(), name="budget"),
    path("analytics/", views.AnalyticsView.as_view(), name="analytics"),
    path("demo/", views.demo_login, name="demo_login"),
    path("demo-signup/", views.demo_signup, name="demo_signup"),
    path("upload/", views.upload_view, name="upload"),
    path("export/", views.export_expenses, name="export-expenses"),
    path("expenses/", views.ExpenseListView.as_view(), name="expense-list"),
    path("expenses/add/", views.ExpenseCreateView.as_view(), name="expense-create"),
    path(
        "expenses/<int:pk>/edit/",
        views.ExpenseUpdateView.as_view(),
        name="expense-edit",
    ),
    path(
        "expenses/bulk-delete/",
        views.ExpenseBulkDeleteView.as_view(),
        name="expense-bulk-delete",
    ),
    path(
        "expenses/<int:pk>/delete/",
        views.ExpenseDeleteView.as_view(),
        name="expense-delete",
    ),
    path(
        "category/create/ajax/", views.create_category_ajax, name="category-create-ajax"
    ),
    path("category/list/", views.CategoryListView.as_view(), name="category-list"),
    path("category/add/", views.CategoryCreateView.as_view(), name="category-create"),
    path(
        "category/<int:pk>/edit/",
        views.CategoryUpdateView.as_view(),
        name="category-edit",
    ),
    path(
        "category/<int:pk>/delete/",
        views.CategoryDeleteView.as_view(),
        name="category-delete",
    ),
    # Income
    path("income/list/", views.IncomeListView.as_view(), name="income-list"),
    path("income/add/", views.IncomeCreateView.as_view(), name="income-create"),
    path("income/<int:pk>/edit/", views.IncomeUpdateView.as_view(), name="income-edit"),
    path(
        "income/<int:pk>/delete/",
        views.IncomeDeleteView.as_view(),
        name="income-delete",
    ),
    # Calendar
    path("calendar/", views.CalendarView.as_view(), name="calendar"),
    path(
        "calendar/<int:year>/<int:month>/",
        views.CalendarView.as_view(),
        name="calendar-month",
    ),
    # Recurring Transactions
    path(
        "recurring/",
        views.RecurringTransactionListView.as_view(),
        name="recurring-list",
    ),
    path(
        "recurring/manage/",
        views.RecurringTransactionManageView.as_view(),
        name="recurring-manage",
    ),
    path("pricing/", views.PricingView.as_view(), name="pricing"),
    path(
        "recurring/create/",
        views.RecurringTransactionCreateView.as_view(),
        name="recurring-create",
    ),
    path(
        "recurring/<int:pk>/edit/",
        views.RecurringTransactionUpdateView.as_view(),
        name="recurring-edit",
    ),
    path(
        "recurring/<int:pk>/delete/",
        views.RecurringTransactionDeleteView.as_view(),
        name="recurring-delete",
    ),
    path(
        "settings/currency/",
        views.CurrencyUpdateView.as_view(),
        name="currency-settings",
    ),
    path(
        "settings/profile/", views.ProfileUpdateView.as_view(), name="profile-settings"
    ),
    path(
        "settings/", views.SettingsHomeView.as_view(), name="settings-home"
    ),  # Settings Home
    path("account/delete/", views.AccountDeleteView.as_view(), name="account-delete"),
    path("tutorial/complete/", views.complete_tutorial, name="complete-tutorial"),
    # Static Pages
    path(
        "privacy-policy/",
        TemplateView.as_view(template_name="privacy_policy.html"),
        name="privacy-policy",
    ),
    path(
        "terms-of-service/",
        TemplateView.as_view(template_name="terms_of_service.html"),
        name="terms-of-service",
    ),
    path(
        "refund-policy/",
        TemplateView.as_view(template_name="refund_policy.html"),
        name="refund-policy",
    ),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path(
        "offline/", TemplateView.as_view(template_name="offline.html"), name="offline"
    ),
    path("contact/", views.ContactView.as_view(), name="contact"),
    # to keep alive on render
    path("ping/", views.ping, name="ping"),
    # Payments
    # Payments
    path("api/create-order/", views_payment.create_order, name="create-order"),
    path("api/verify-payment/", views_payment.verify_payment, name="verify-payment"),
    path(
        "api/resend-verification/",
        views.resend_verification_email,
        name="resend-verification",
    ),
    # Notification URLs
    path(
        "notifications/", views.NotificationListView.as_view(), name="notification-list"
    ),
    path(
        "notifications/mark-all-read/",
        views.mark_notifications_read,
        name="mark-all-read",
    ),
    path(
        "notifications/<int:pk>/read/",
        views.mark_single_notification_read,
        name="mark-single-notification-read",
    ),
    path(
        "api/cron/send-notifications/",
        views.trigger_notifications,
        name="cron-send-notifications",
    ),
    # Sentry Debug
    path("sentry-debug/", lambda request: 1 / 0),
    path("income/list/", views.IncomeListView.as_view(), name="income-list"),
    path("income/add/", views.IncomeCreateView.as_view(), name="income-create"),
    path("income/<int:pk>/edit/", views.IncomeUpdateView.as_view(), name="income-edit"),
    path(
        "income/<int:pk>/delete/",
        views.IncomeDeleteView.as_view(),
        name="income-delete",
    ),
    path("calendar/", views.CalendarView.as_view(), name="calendar"),
    path(
        "calendar/<int:year>/<int:month>/",
        views.CalendarView.as_view(),
        name="calendar-month",
    ),
    path(
        "recurring/",
        views.RecurringTransactionListView.as_view(),
        name="recurring-list",
    ),
    path(
        "recurring/manage/",
        views.RecurringTransactionManageView.as_view(),
        name="recurring-manage",
    ),
    path("pricing/", views.PricingView.as_view(), name="pricing"),
    path(
        "recurring/create/",
        views.RecurringTransactionCreateView.as_view(),
        name="recurring-create",
    ),
    path(
        "recurring/<int:pk>/edit/",
        views.RecurringTransactionUpdateView.as_view(),
        name="recurring-edit",
    ),
    path(
        "recurring/<int:pk>/delete/",
        views.RecurringTransactionDeleteView.as_view(),
        name="recurring-delete",
    ),
    path(
        "settings/currency/",
        views.CurrencyUpdateView.as_view(),
        name="currency-settings",
    ),
    path(
        "settings/profile/", views.ProfileUpdateView.as_view(), name="profile-settings"
    ),
    path(
        "settings/", views.SettingsHomeView.as_view(), name="settings-home"
    ),  # Settings Home
    path("account/delete/", views.AccountDeleteView.as_view(), name="account-delete"),
    path("tutorial/complete/", views.complete_tutorial, name="complete-tutorial"),
    path("api/predict-category/", views.predict_category_view, name="predict-category"),

    # Shared Expenses
    path('balance-summary/', views.BalanceSummaryView.as_view(), name='balance-summary'),

    # Friend Management (AJAX)
    path('api/friend/create/', views.create_friend_ajax, name='friend-create-ajax'),
    path('api/friend/<int:pk>/update/', views.update_friend_ajax, name='friend-update-ajax'),
    path('api/friend/<int:pk>/delete/', views.delete_friend_ajax, name='friend-delete-ajax'),

    # Friends Ledger
    path('friends/', views_friends.FriendListView.as_view(), name='friend-list'),
    path('friends/add/', views_friends.FriendCreateView.as_view(), name='friend-add'),
    path('friends/<int:pk>/', views_friends.FriendDetailView.as_view(), name='friend-detail'),
    path('friends/<int:pk>/edit/', views_friends.FriendUpdateView.as_view(), name='friend-edit'),
    path('friends/<int:pk>/delete/', views_friends.FriendDeleteView.as_view(), name='friend-delete'),
    path('friends/<int:friend_pk>/settle/', views_friends.SettlementCreateView.as_view(), name='settlement-create'),

    # Payment Sources (Bank Accounts, Wallets, Cash)
    path('accounts/', views_accounts.PaymentSourceListView.as_view(), name='payment-source-list'),
    path('accounts/add/', views_accounts.PaymentSourceCreateView.as_view(), name='payment-source-add'),
    path('accounts/<int:pk>/', views_accounts.PaymentSourceDetailView.as_view(), name='payment-source-detail'),
    path('accounts/<int:pk>/edit/', views_accounts.PaymentSourceUpdateView.as_view(), name='payment-source-edit'),
    path('accounts/<int:pk>/delete/', views_accounts.PaymentSourceDeleteView.as_view(), name='payment-source-delete'),

    # Credit Cards
    path('cards/', views_creditcards.CreditCardListView.as_view(), name='credit-card-list'),
    path('cards/add/', views_creditcards.CreditCardCreateView.as_view(), name='credit-card-add'),
    path('cards/<int:pk>/', views_creditcards.CreditCardDetailView.as_view(), name='credit-card-detail'),
    path('cards/<int:pk>/edit/', views_creditcards.CreditCardUpdateView.as_view(), name='credit-card-edit'),
    path('cards/<int:pk>/delete/', views_creditcards.CreditCardDeleteView.as_view(), name='credit-card-delete'),
    path('cards/<int:pk>/pay/', views_creditcards.CreditCardPaymentView.as_view(), name='credit-card-pay'),

    path("sentry-debug/", lambda request: 1 / 0),
]
