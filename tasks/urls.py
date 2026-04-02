# Third party imports
from django.urls import path

# Local folder imports
from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.TaskListView.as_view(), name="list"),
    path("add/", views.TaskCreateView.as_view(), name="add"),
    path("<int:pk>/", views.TaskDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.TaskEditView.as_view(), name="edit"),
    path("<int:pk>/close/", views.TaskCloseView.as_view(), name="close"),
    path("<int:pk>/delete/", views.delete_task, name="delete"),
    path("<int:pk>/reopen/", views.reopen_task, name="reopen"),
    path("<int:pk>/resign/", views.resign_task, name="resign"),
    path("<int:pk>/take/", views.take_task, name="take"),
    path("<int:pk>/vote/", views.vote_task, name="vote"),
    path("<int:pk>/evaluate/", views.evaluate_task, name="evaluate"),
]
