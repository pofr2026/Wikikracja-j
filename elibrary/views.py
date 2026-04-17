# Third party imports
from django.contrib.auth.decorators import login_required

# import os
from django.contrib.auth.mixins import LoginRequiredMixin
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

        # Posts sorted by category priority, then by date within each category
        if sort == 'date':
            post_order = 'updated' if order == 'asc' else '-updated'
        else:
            post_order = 'updated' if order == 'asc' else '-updated'

        # Build category groups for posts
        categories = list(PostCategory.objects.all())  # already ordered by priority, name
        category_groups = []
        for cat in categories:
            posts = Post.objects.filter(
                category=cat, is_archived=False
            ).order_by(post_order)
            if posts.exists():
                category_groups.append({'category': cat, 'posts': posts})

        # Posts without category → "Różne" group at the end
        uncategorized = Post.objects.filter(
            category__isnull=True, is_archived=False
        ).order_by(post_order)
        if uncategorized.exists():
            category_groups.append({'category': None, 'posts': uncategorized})

        context['category_groups'] = category_groups

        # Books sorted
        if sort == 'date':
            book_qs = Book.objects.all().order_by('id' if order == 'asc' else '-id')
        else:
            book_qs = Book.objects.all().order_by('id' if order == 'asc' else '-id')
        context['books'] = book_qs

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
