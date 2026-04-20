# Third party imports
from django.contrib.auth.decorators import login_required

# import os
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Prefetch
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, ListView, UpdateView
from PIL import Image

# First party imports
from board.models import Post, PostCategory
from elibrary.forms import UpdateBookForm
from elibrary.models import Book

ELIBRARY_CACHE_KEY = "elibrary_data_v1"
ELIBRARY_CACHE_TTL = 3600


def invalidate_elibrary_cache():
    cache.delete(ELIBRARY_CACHE_KEY)


def _load_elibrary_data():
    """
    Fetch posts (grouped by category) and books. Cached globally in Redis (TTL 1h).
    Returns dict: {'category_groups': [...], 'books': [...]}
    Sorting is applied per-request in get_context_data after cache retrieval.
    """
    cached = cache.get(ELIBRARY_CACHE_KEY)
    if cached is not None:
        return cached

    # Single query: all non-archived posts with their categories — eliminates N+1
    all_posts = list(
        Post.objects.filter(is_archived=False)
        .select_related('category', 'author')
        .order_by('category__priority', 'category__name', '-updated')
    )
    categories = list(PostCategory.objects.all())

    # Group in Python — no extra queries per category
    posts_by_cat = {}
    uncategorized = []
    for post in all_posts:
        if post.category_id:
            posts_by_cat.setdefault(post.category_id, []).append(post)
        else:
            uncategorized.append(post)

    category_groups_raw = []
    for cat in categories:
        cat_posts = posts_by_cat.get(cat.pk, [])
        if cat_posts:
            category_groups_raw.append({'category': cat, 'posts': cat_posts})
    if uncategorized:
        category_groups_raw.append({'category': None, 'posts': uncategorized})

    books = list(Book.objects.select_related('uploader').order_by('-id'))

    result = {'category_groups_raw': category_groups_raw, 'books': books}
    cache.set(ELIBRARY_CACHE_KEY, result, ELIBRARY_CACHE_TTL)
    return result


@login_required
def add(request: HttpRequest):
    if request.method == 'POST':
        form = UpdateBookForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.uploader = request.user
            obj.save()

            image = Image.open(obj.cover)
            image = image.resize((200, 300), Image.LANCZOS)
            # upload_file_name = obj.cover.file.name
            # print(upload_file_name)
            image.save('media/elibrary/' + str(obj.id) + '.png')
            obj.cover.name = 'elibrary/' + str(obj.id) + '.png'
            # form.save_m2m()  # taggit
            # os.remove(upload_file_name)  # delete original file
            obj.save()
            return redirect('elibrary:book_list')
    else:
        form = UpdateBookForm()
    return render(request, 'elibrary/add.html', {
        'form': form
    })


class BookList(LoginRequiredMixin, ListView):
    def get_queryset(self):
        return Book.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sort = self.request.GET.get('sort', 'date')
        order = self.request.GET.get('order', 'desc')
        context['current_sort'] = sort
        context['current_order'] = order

        data = _load_elibrary_data()
        reverse_order = (order == 'desc')

        # Sort posts within each category group in Python
        category_groups = []
        for group in data['category_groups_raw']:
            sorted_posts = sorted(
                group['posts'],
                key=lambda p: p.updated,
                reverse=reverse_order,
            )
            category_groups.append({'category': group['category'], 'posts': sorted_posts})
        context['category_groups'] = category_groups

        # Sort books in Python
        context['books'] = sorted(data['books'], key=lambda b: b.id, reverse=reverse_order)

        return context


class BookDeleteView(LoginRequiredMixin, DeleteView):
    model = Book
    template_name = 'elibrary/book_confirm_delete.html'
    # Files are not physicaly deleted. This needs to be changed
    success_url = reverse_lazy('elibrary:book_list')

    def dispatch(self, request, *args, **kwargs):
        # Ensure only the uploader can delete their own book
        obj = self.get_object()
        if obj.uploader != request.user:
            return redirect('elibrary:book_list')
        return super().dispatch(request, *args, **kwargs)


class BookDetailView(LoginRequiredMixin, DetailView):
    model = Book

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['book_list'] = Book.objects.all()

        # Previous and Next
        obj = get_object_or_404(Book, pk=self.kwargs['pk'])
        # kandydaci czy obywatele? Na razie wszyscy
        prev = Book.objects.filter(pk__lt=obj.pk).order_by('-pk').first()
        next = Book.objects.filter(pk__gt=obj.pk).order_by('pk').first()

        context['prev'] = prev
        context['next'] = next

        return context

    # success_url = reverse_lazy('elibrary:elibrary')
    queryset = Book.objects.all()

    def get_object(self):
        obj = super().get_object()
        # Record the last accessed date
        return obj


class BookUpdateView(LoginRequiredMixin, UpdateView):
    model = Book
    fields = ['title', 'author', 'abstract', 'cover', 'file_epub', 'file_mobi', 'file_pdf']

    def form_valid(self, form):
        if form.instance.cover == "":
            form.instance.cover = 'elibrary/default.png'
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('elibrary:book-detail', kwargs={
            'pk': self.object.pk
        })
