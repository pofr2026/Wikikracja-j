# Third party imports
from django.urls import path

# Local folder imports
from . import views

app_name = 'board'

urlpatterns = [
    path('', views.board, name='start'),
    path('create/', views.create_post, name='create_post'),
    path('edit/<int:pk>/', views.edit_post, name='edit_post'),
    path('view/<int:pk>/', views.view_post, name='view_post'),
    path('delete/<int:pk>/', views.delete_post, name='delete_post'),
    path('archive/', views.archive, name='archive'),
    path('category/', views.PostCategoryListView.as_view(), name='category_list'),
    path('category/create/', views.PostCategoryCreateView.as_view(), name='category_create'),
    path('category/<int:pk>/update/', views.PostCategoryUpdateView.as_view(), name='category_update'),
    path('category/<int:pk>/delete/', views.PostCategoryDeleteView.as_view(), name='category_delete'),
]
