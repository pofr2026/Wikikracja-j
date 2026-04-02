# Third party imports
from django.contrib.auth.decorators import login_required

# import os
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, DetailView, ListView, UpdateView
from PIL import Image

# First party imports
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
    # template_name = 'elibrary/elibrary.html'

    def get_queryset(self):
        return Book.objects.all()


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
