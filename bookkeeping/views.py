# Third party imports
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

# Local folder imports
from .forms import TransactionForm
from .models import Category, Partner, Transaction

# #########################  Category ###########################


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'bookkeeping/category_list.html'


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    fields = '__all__'
    success_url = reverse_lazy('bookkeeping:category_list')


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    fields = '__all__'
    success_url = reverse_lazy('bookkeeping:category_list')


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    success_url = reverse_lazy('bookkeeping:category_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all transactions using this category
        related_transactions = Transaction.objects.filter(category=self.object)

        context['related_transactions'] = related_transactions
        context['has_dependencies'] = related_transactions.exists()

        # Add error message if it exists in session
        if 'delete_error' in self.request.session:
            context['error'] = self.request.session.pop('delete_error')

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Check if there are related transactions
        if Transaction.objects.filter(category=self.object).exists():
            # Don't allow deletion if there are related transactions
            request.session['delete_error'] = _("Cannot delete category because it is in use. Remove all transactions that use it first.")
            return redirect('bookkeeping:category_delete', pk=self.object.pk)

        try:
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            request.session['delete_error'] = str(e)
            return redirect('bookkeeping:category_delete', pk=self.object.pk)


# #########################  Partner ###########################


class PartnerListView(LoginRequiredMixin, ListView):
    model = Partner
    template_name = 'bookkeeping/partner_list.html'


class PartnerCreateView(LoginRequiredMixin, CreateView):
    model = Partner
    fields = '__all__'
    success_url = reverse_lazy('bookkeeping:partner_list')


class PartnerUpdateView(LoginRequiredMixin, UpdateView):
    model = Partner
    fields = '__all__'
    success_url = reverse_lazy('bookkeeping:partner_list')


class PartnerDeleteView(LoginRequiredMixin, DeleteView):
    model = Partner
    success_url = reverse_lazy('bookkeeping:partner_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all transactions using this partner
        related_transactions = Transaction.objects.filter(partner=self.object)

        context['related_transactions'] = related_transactions
        context['has_dependencies'] = related_transactions.exists()

        # Add error message if it exists in session
        if 'delete_error' in self.request.session:
            context['error'] = self.request.session.pop('delete_error')

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Check if there are related transactions
        if Transaction.objects.filter(partner=self.object).exists():
            # Don't allow deletion if there are related transactions
            request.session['delete_error'] = _("Cannot delete partner because it is in use. Remove all transactions that use it first.")
            return redirect('bookkeeping:partner_delete', pk=self.object.pk)

        try:
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            request.session['delete_error'] = str(e)
            return redirect('bookkeeping:partner_delete', pk=self.object.pk)


# #########################  Transaction ###########################


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'bookkeeping/transaction_list.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        # Create a list combining both transaction types
        incoming = Transaction.objects.filter(type=Transaction.INCOMING).order_by('-payment_received_date')
        outgoing = Transaction.objects.filter(type=Transaction.OUTGOING).order_by('-payment_received_date')

        # Create a combined list with type information
        transactions = []
        for item in incoming:
            transactions.append({
                'id': item.id,
                'type': 'I',
                'payment_received_date': item.payment_received_date,
                'partner': item.partner,
                'category': item.category,
                'amount': item.amount,
                'note': item.note,
                'obj': item
            })

        for item in outgoing:
            transactions.append({
                'id': item.id,
                'type': 'O',
                'payment_received_date': item.payment_received_date,
                'partner': item.partner,
                'category': item.category,
                'amount': item.amount,
                'note': item.note,
                'obj': item
            })

        # Sort by payment date and ID (oldest first for balance calculation)
        sorted_transactions = sorted(transactions, key=lambda x: (x['payment_received_date'] is None, x['payment_received_date'], x['id']))

        # Calculate running balance
        balance = 0
        for transaction in sorted_transactions:
            if transaction['type'] == 'I':
                balance += transaction['amount']
            else:
                balance -= transaction['amount']
            transaction['balance'] = balance

        # Return sorted by most recent first for display (date DESC, ID ASC within same date)
        result = []
        current_date = None
        date_group = []

        for transaction in reversed(sorted_transactions):
            if transaction['payment_received_date'] != current_date:
                if date_group:
                    result.extend(date_group)
                date_group = [transaction]
                current_date = transaction['payment_received_date']
            else:
                date_group.append(transaction)

        if date_group:
            result.extend(date_group)

        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class TransactionCreateView(LoginRequiredMixin, View):
    template_name = 'bookkeeping/transaction_form.html'

    def get(self, request):
        # Just use a single transaction form
        transaction_form = TransactionForm()
        return render(request, self.template_name, {
            'transaction_form': transaction_form,
        })

    def post(self, request):
        transaction_form = TransactionForm(request.POST)

        if transaction_form.is_valid():
            transaction_data = transaction_form.cleaned_data

            # Create a new transaction
            transaction = Transaction(type=transaction_data['type'], partner=transaction_data['partner'], category=transaction_data['category'], amount=transaction_data['amount'], payment_received_date=transaction_data['payment_received_date'], note=transaction_data['note'], author=request.user)

            # Set the current user and save
            transaction.created_date = timezone.now()
            transaction.save()

            return redirect('bookkeeping:transaction_list')

        return render(request, self.template_name, {
            'transaction_form': transaction_form,
        })


class TransactionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'bookkeeping/transaction_form.html'

    def test_func(self):
        transaction = self.get_object()
        return self.request.user == transaction.author

    def get_success_url(self):
        # Check if 'next' parameter exists in the request
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('bookkeeping:transaction_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ensure the form is accessible in the template as transaction_form
        if 'form' in context:
            context['transaction_form'] = context['form']
        return context


class TransactionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Transaction
    template_name = 'bookkeeping/transaction_confirm_delete.html'
    success_url = reverse_lazy('bookkeeping:transaction_list')

    def test_func(self):
        transaction = self.get_object()
        return self.request.user == transaction.author


# #########################  Report ###########################


class ReportView(LoginRequiredMixin, View):
    template_name = 'bookkeeping/report_list.html'

    def get(self, request, year=None):
        # Get year from query parameters or URL, fallback to current year
        try:
            year = int(request.GET.get('year', year)) if year or request.GET.get('year') else timezone.now().year
        except (ValueError, TypeError):
            year = timezone.now().year

        # Get categories and prepare movement data
        categories = Category.objects.all().order_by('name')
        category_movements = {}
        all_years_category_movements = {}

        # Fetch transaction totals by category and type in a single query per type
        outgoing_by_category = dict(Transaction.objects.filter(payment_received_date__year=year, type=Transaction.OUTGOING).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))

        incoming_by_category = dict(Transaction.objects.filter(payment_received_date__year=year, type=Transaction.INCOMING).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))

        # Fetch transaction totals by category and type for ALL years
        all_years_outgoing_by_category = dict(Transaction.objects.filter(type=Transaction.OUTGOING).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))

        all_years_incoming_by_category = dict(Transaction.objects.filter(type=Transaction.INCOMING).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))

        # Calculate overall totals across all categories
        total_net = (sum(value or 0 for value in incoming_by_category.values()) - sum(value or 0 for value in outgoing_by_category.values()))
        all_years_total_net = (sum(value or 0 for value in all_years_incoming_by_category.values()) - sum(value or 0 for value in all_years_outgoing_by_category.values()))

        # Process all categories including uncategorized (None)
        all_category_ids = set(list(outgoing_by_category.keys()) + list(incoming_by_category.keys()))
        all_years_category_ids = set(list(all_years_outgoing_by_category.keys()) + list(all_years_incoming_by_category.keys()))

        # Add entries for each category with movement
        for category in categories:
            outgoing = outgoing_by_category.get(category.id, 0) or 0
            incoming = incoming_by_category.get(category.id, 0) or 0

            if outgoing > 0 or incoming > 0:
                category_movements[category] = {
                    'outgoing': outgoing,
                    'incoming': incoming,
                    'net': incoming - outgoing
                }

            # Add all years data for this category
            all_years_outgoing = all_years_outgoing_by_category.get(category.id, 0) or 0
            all_years_incoming = all_years_incoming_by_category.get(category.id, 0) or 0

            if all_years_outgoing > 0 or all_years_incoming > 0:
                all_years_category_movements[category] = {
                    'outgoing': all_years_outgoing,
                    'incoming': all_years_incoming,
                    'net': all_years_incoming - all_years_outgoing
                }

            # Remove from all_category_ids to track what's left
            if category.id in all_category_ids:
                all_category_ids.remove(category.id)

            if category.id in all_years_category_ids:
                all_years_category_ids.remove(category.id)

        # Handle uncategorized transactions (None category)
        if None in all_category_ids:
            outgoing = outgoing_by_category.get(None, 0) or 0
            incoming = incoming_by_category.get(None, 0) or 0

            if outgoing > 0 or incoming > 0:
                category_movements[None] = {
                    'outgoing': outgoing,
                    'incoming': incoming,
                    'net': incoming - outgoing
                }

        # Handle uncategorized transactions for all years (None category)
        if None in all_years_category_ids:
            all_years_outgoing = all_years_outgoing_by_category.get(None, 0) or 0
            all_years_incoming = all_years_incoming_by_category.get(None, 0) or 0

            if all_years_outgoing > 0 or all_years_incoming > 0:
                all_years_category_movements[None] = {
                    'outgoing': all_years_outgoing,
                    'incoming': all_years_incoming,
                    'net': all_years_incoming - all_years_outgoing
                }

        # Get available years for the dropdown
        available_years = (Transaction.objects.dates('payment_received_date', 'year').values_list('payment_received_date__year', flat=True).distinct().order_by('-payment_received_date__year'))

        context = {
            'category_movements': category_movements,
            'all_years_category_movements': all_years_category_movements,
            'total_net': total_net,
            'all_years_total_net': all_years_total_net,
            'year': year,
            'available_years': available_years,
        }

        return render(request, self.template_name, context)
