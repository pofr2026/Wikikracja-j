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
]
