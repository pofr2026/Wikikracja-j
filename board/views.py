# Third party imports
from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

# Local folder imports
from .forms import PostForm
from .models import Post


def board(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        posts_all = Post.objects.filter(is_archived=False)
        posts_pinned = posts_all.filter(is_important=True).order_by('-updated')
        posts_not_pinned = posts_all.filter(is_important=False).order_by('-updated')
    else:
        posts_public = Post.objects.filter(is_public=True, is_archived=False)
        posts_pinned = posts_public.filter(is_important=True).order_by('-updated')
        posts_not_pinned = posts_public.filter(is_important=False).order_by('-updated')

    return render(
        request,
        'board/board.html',
        {
            'posts_pinned': posts_pinned,
            'posts_not_pinned': posts_not_pinned
        },
    )


def archive(request: HttpRequest) -> HttpResponse:
    posts_archived: QuerySet[Post] = Post.objects.filter(is_archived=True).order_by('-updated')
    return render(request, 'board/archive.html', {
        'posts': posts_archived
    })


@login_required
def create_post(request: HttpRequest):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('board:view_post', post.pk)
    else:
        form = PostForm()
    return render(request, 'board/create_post.html', {
        'form': form
    })


@login_required
def edit_post(request: HttpRequest, pk: int):
    post = get_object_or_404(Post, pk=pk)

    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('board:view_post', pk)
    else:
        form = PostForm(instance=post)
    return render(request, 'board/edit_post.html', {
        'form': form
    })


def view_post(request: HttpRequest, pk: int):
    post = get_object_or_404(Post, pk=pk)  # Only published posts can be viewed
    return render(request, 'board/post_detail.html', {
        'post': post
    })


@login_required
def delete_post(request: HttpRequest, pk: int):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        post.delete()
        return redirect('board:start')
    return render(request, 'board/post_confirm_delete.html', {
        'post': post
    })
