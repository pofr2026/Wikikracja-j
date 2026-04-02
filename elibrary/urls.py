# Third party imports
from django.urls import path

# First party imports
from elibrary import views as v

app_name = 'elibrary'

urlpatterns = [
    path('new', v.add, name='add'),
    path('', v.BookList.as_view(), name='book_list'),
    path('<int:pk>/detail/', v.BookDetailView.as_view(), name='book-detail'),
    path('<int:pk>/update/', v.BookUpdateView.as_view(), name='book-update'),
    path('<int:pk>/delete/', v.BookDeleteView.as_view(), name='book-delete'),
]
