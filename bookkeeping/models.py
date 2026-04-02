# Standard library imports
from datetime import datetime

# Third party imports
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name=_("Name"))

    def __str__(self):
        return self.name


class Partner(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name=_("Name"))
    email = models.EmailField(null=True, blank=True, verbose_name=_("email"))
    phone = models.CharField(max_length=200, null=True, blank=True, verbose_name=_("Phone"))
    web_page = models.CharField(max_length=200, null=True, blank=True, verbose_name=_("Web page"))
    address = models.CharField(max_length=200, null=True, blank=True, verbose_name=_("Address"))
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("City"))
    country = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Country"))

    def __str__(self):
        return self.name


class Transaction(models.Model):
    INCOMING = 'I'
    OUTGOING = 'O'
    TYPES = [
        (INCOMING, _('Incoming')),
        (OUTGOING, _('Outgoing')),
    ]
    type = models.CharField(max_length=1, choices=TYPES, default=INCOMING, verbose_name=_("Type"))

    created_date = models.DateField(auto_now_add=True, verbose_name=_("Created"))
    payment_received_date = models.DateField(null=True, blank=True, default=datetime.now, editable=True, verbose_name=_("Payment received date"))

    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Category"))
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, null=True, blank=False, verbose_name=_("Partner"))
    amount = models.FloatField(null=True, blank=False, verbose_name=_("Outgoing amount"))
    note = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Note"))
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Author"), related_name='transactions')

    def __str__(self):
        return f"{self.payment_received_date} - {self.partner} {self.type} {self.amount}"
