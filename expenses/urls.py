from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('', views.home_view, name='home'),
    path('upload/', views.upload_view, name='upload'),
    path('expenses/', views.ExpenseListView.as_view(), name='expense-list'),
    path('expenses/add/', views.ExpenseCreateView.as_view(), name='expense-create'),
    path('expenses/<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense-edit'),
    path('expenses/<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense-delete'),
    path('category/list/', views.CategoryListView.as_view(), name='category-list'),
    path('category/add/', views.CategoryCreateView.as_view(), name='category-create'),
    path('category/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category-edit'),
    path('category/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category-delete'),
]
