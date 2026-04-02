# Standard library imports
import math

# Third party imports
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models, transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

# Local folder imports
from .forms import TaskForm, TaskStatusForm
from .models import Task, TaskEvaluation, TaskVote

PRIORITY_LABELS = {
    "critical": gettext_lazy("Critical"),
    "important": gettext_lazy("Important"),
    "beneficial": gettext_lazy("Beneficial"),
    "rejected": gettext_lazy("Rejected"),
}


def _assign_priorities(tasks):
    for task in tasks:
        task.priority_label = None
        task.priority_category = None

    non_rejected = [t for t in tasks if (t.votes_score or 0) >= -1]
    rejected = [t for t in tasks if (t.votes_score or 0) <= -2]
    total = len(non_rejected)

    def mark(task, category):
        task.priority_category = category
        task.priority_label = PRIORITY_LABELS[category]

    if total == 0:
        for task in rejected:
            mark(task, "rejected")
        return

    critical_limit = max(1, math.ceil(total * 0.2))
    important_limit = critical_limit + math.ceil(total * 0.3)

    for idx, task in enumerate(non_rejected):
        if idx < critical_limit:
            mark(task, "critical")
        elif idx < important_limit:
            mark(task, "important")
        else:
            mark(task, "beneficial")

    for task in rejected:
        mark(task, "rejected")


class TaskListView(LoginRequiredMixin, TemplateView):
    template_name = "tasks/task_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = Task.objects.with_metrics().order_by("-votes_score", "-updated_at")

        active_tasks = list(queryset.filter(status=Task.Status.ACTIVE))
        _assign_priorities(active_tasks)
        rejected_active = [task for task in active_tasks if task.priority_category == "rejected"]
        active_non_rejected = [task for task in active_tasks if task.priority_category != "rejected"]
        active_with_owner = [task for task in active_non_rejected if task.assigned_to and ((task.votes_up or 0) - (task.votes_down or 0) >= 2)]
        awaiting_tasks = [task for task in active_non_rejected if task not in active_with_owner]
        finished_tasks = list(queryset.exclude(status=Task.Status.ACTIVE))
        _assign_priorities(finished_tasks)
        rejected_tasks = [task for task in finished_tasks if task.priority_category == "rejected"]
        completed_tasks = [task for task in finished_tasks if task.priority_category != "rejected" and task.status == Task.Status.COMPLETED]
        cancelled_tasks = [task for task in finished_tasks if task.priority_category != "rejected" and task.status == Task.Status.CANCELLED]

        all_tasks = active_tasks + finished_tasks
        if self.request.user.is_authenticated:
            user_votes = TaskVote.objects.filter(
                user=self.request.user,
                task_id__in=[task.id for task in all_tasks],
            ).values_list("task_id", "value")
            vote_by_task_id = dict(user_votes)
            for task in all_tasks:
                task.user_vote_value = vote_by_task_id.get(task.id)

        # Add chat room pulse class for tasks with unseen messages
        if self.request.user.is_authenticated:
            for task in all_tasks:
                task.chat_room_pulse_class = task.get_chat_room_pulse_class(self.request.user)

        context.update({
            "active_tasks": active_with_owner,
            "awaiting_tasks": awaiting_tasks,
            "finished_completed": completed_tasks,
            "finished_rejected": rejected_tasks + rejected_active,
            "finished_cancelled": cancelled_tasks,
        })
        return context


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"
    success_url = reverse_lazy("tasks:list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


@require_POST
@login_required
def take_task(request: HttpRequest, pk: int) -> HttpResponse:
    task = get_object_or_404(Task, pk=pk)
    task.assigned_to = request.user
    task.save(update_fields=["assigned_to", "updated_at"])
    return redirect(request.POST.get("next") or "tasks:list")


@require_POST
@login_required
def resign_task(request: HttpRequest, pk: int) -> HttpResponse:
    task = get_object_or_404(Task, pk=pk)
    next_url = request.POST.get("next")
    if task.assigned_to != request.user:
        if next_url:
            return redirect(next_url)
        return redirect("tasks:detail", pk=pk)

    task.assigned_to = None
    task.save(update_fields=["assigned_to", "updated_at"])
    if next_url:
        return redirect(next_url)
    return redirect("tasks:list")


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/task_detail.html"
    context_object_name = "task"

    def get_queryset(self):
        return Task.objects.with_metrics()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = context["task"]
        if task.is_active:
            reference_tasks = list(Task.objects.with_metrics().filter(status=Task.Status.ACTIVE).order_by("-votes_score", "-updated_at"))
        else:
            reference_tasks = list(Task.objects.with_metrics().exclude(status=Task.Status.ACTIVE).order_by("-votes_score", "-updated_at"))
        _assign_priorities(reference_tasks)
        priority_map = {
            t.id: getattr(t, "priority_label", None) for t in reference_tasks
        }
        current_label = getattr(task, "priority_label", None)
        task.priority_label = priority_map.get(task.id, current_label or task.get_status_display())
        priority_map = {
            t.id: (
                getattr(t, "priority_label", None),
                getattr(t, "priority_category", None),
            ) for t in reference_tasks
        }
        current_label, current_category = priority_map.get(
            task.id,
            (
                getattr(task, "priority_label", None),
                getattr(task, "priority_category", None),
            ),
        )
        task.priority_label = current_label or task.get_status_display()
        task.priority_category = current_category
        context["helping_votes"] = (TaskVote.objects.filter(task=task, value=TaskVote.Value.UP).select_related("user").order_by("updated_at", "id"))
        if self.request.user.is_authenticated:
            vote = TaskVote.objects.filter(task=task, user=self.request.user).first()
            context["user_vote_value"] = vote.value if vote else None

            # Check if chat room has unseen messages
            task.chat_room_pulse_class = task.get_chat_room_pulse_class(self.request.user)
        context["task"] = task
        return context


class TaskEditView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"

    def dispatch(self, request, *args, **kwargs):
        task = self.get_object()
        if task.assigned_to != request.user:
            return redirect("tasks:detail", pk=task.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("tasks:detail", kwargs={
            "pk": self.object.pk
        })


class TaskCloseView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskStatusForm
    template_name = "tasks/task_close.html"

    def dispatch(self, request, *args, **kwargs):
        task = self.get_object()
        if task.assigned_to != request.user:
            return redirect("tasks:detail", pk=task.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("tasks:detail", kwargs={
            "pk": self.object.pk
        })


@require_POST
@login_required
def vote_task(request: HttpRequest, pk: int) -> HttpResponse:
    task = get_object_or_404(Task.objects.with_metrics(), pk=pk)
    value = int(request.POST.get("value", 0))
    if value not in (TaskVote.Value.DOWN, TaskVote.Value.UP):
        return redirect(request.POST.get("next") or "tasks:list")

    with transaction.atomic():
        vote = TaskVote.objects.filter(task=task, user=request.user).first()
        if vote and vote.value == value:
            vote.delete()
        else:
            if not vote:
                vote = TaskVote(task=task, user=request.user, value=value)
                vote.save()
            else:
                vote.value = value
                vote.save(update_fields=["value", "updated_at"])

        # Refresh score and set rejected if sum of votes <= -2
        task.refresh_from_db(fields=["status", "updated_at"])
        metrics = Task.objects.filter(pk=task.pk).annotate(votes_score=Coalesce(Sum("votes__value"), 0)).values("votes_score", "status").first()
        votes_score = metrics["votes_score"] if metrics else 0
        if votes_score <= -2 and task.status != Task.Status.REJECTED:
            Task.objects.filter(pk=task.pk).update(status=Task.Status.REJECTED, updated_at=models.F("updated_at"))
            task.status = Task.Status.REJECTED
    return redirect(request.POST.get("next") or "tasks:list")


@require_POST
@login_required
def reopen_task(request: HttpRequest, pk: int) -> HttpResponse:
    task = get_object_or_404(Task, pk=pk)
    next_url = request.POST.get("next")
    if task.is_active:
        if next_url:
            return redirect(next_url)
        return redirect("tasks:detail", pk=pk)

    TaskVote.objects.filter(task=task).delete()
    task.status = Task.Status.ACTIVE
    task.save(update_fields=["status", "updated_at"])
    if next_url:
        return redirect(next_url)
    return redirect("tasks:list")


@require_POST
@login_required
def evaluate_task(request: HttpRequest, pk: int) -> HttpResponse:
    task = get_object_or_404(Task, pk=pk)
    value = request.POST.get("value")
    if value not in (
        TaskEvaluation.Value.SUCCESS,
        TaskEvaluation.Value.FAILURE,
    ):
        return redirect(request.POST.get("next") or "tasks:list")

    evaluation = TaskEvaluation.objects.filter(task=task, user=request.user).first()
    if evaluation and evaluation.value == value:
        evaluation.delete()
    else:
        if not evaluation:
            evaluation = TaskEvaluation(task=task, user=request.user, value=value)
            evaluation.save()
        else:
            evaluation.value = value
            evaluation.save(update_fields=["value", "updated_at"])
    return redirect(request.POST.get("next") or "tasks:list")


@require_POST
@login_required
def delete_task(request: HttpRequest, pk: int) -> HttpResponse:
    task = get_object_or_404(Task, pk=pk)
    if task.created_by != request.user:
        return redirect("tasks:detail", pk=pk)

    if task.status == Task.Status.COMPLETED:
        return redirect("tasks:detail", pk=pk)

    task.delete()
    return redirect("tasks:list")
