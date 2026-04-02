# Third party imports
from django.urls import path

# Local folder imports
from .views import (
    CategoryCreateView,
    CategoryDeleteView,
    CategoryListView,
    CategoryUpdateView,
    PartnerCreateView,
    PartnerDeleteView,
    PartnerListView,
    PartnerUpdateView,
    ReportView,
    TransactionCreateView,
    TransactionDeleteView,
    TransactionListView,
    TransactionUpdateView,
)

app_name = 'bookkeeping'

urlpatterns = [
    # Transaction URL (combined incoming/outgoing)
    path('transaction/', TransactionListView.as_view(), name='transaction_list'),
    path('transaction/create/', TransactionCreateView.as_view(), name='transaction_create'),
    path('transaction/<int:pk>/update/', TransactionUpdateView.as_view(), name='transaction_update'),
    path('transaction/<int:pk>/delete/', TransactionDeleteView.as_view(), name='transaction_delete'),

    # Partner URLs
    path('partner/', PartnerListView.as_view(), name='partner_list'),
    path('partner/create/', PartnerCreateView.as_view(), name='partner_create'),
    path('partner/<int:pk>/update/', PartnerUpdateView.as_view(), name='partner_update'),
    path('partner/<int:pk>/delete/', PartnerDeleteView.as_view(), name='partner_delete'),

    # Category URLs
    path('category/', CategoryListView.as_view(), name='category_list'),
    path('category/create/', CategoryCreateView.as_view(), name='category_create'),
    path('category/<int:pk>/update/', CategoryUpdateView.as_view(), name='category_update'),
    path('category/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category_delete'),

    # Report URLs
    path('report/', ReportView.as_view(), name='report_list'),
    path('report/<int:year>/', ReportView.as_view(), name='report_by_year'),

    # Default view
    path('', TransactionListView.as_view(), name='index'),
]
