# Third party imports
import django_tables2 as tables

# First party imports
from obywatele.models import Uzytkownik

# https://django-tables2.readthedocs.io/en/latest/pages/filtering.html


class UzytkownikTable(tables.Table):
    class Meta:
        model = Uzytkownik
        fields = ('uid', 'city', 'responsibilities', 'hobby', 'to_give_away', 'to_borrow', 'for_sale', 'i_need', 'skills', 'knowledge', 'want_to_learn', 'business', 'job', 'other', 'why')
        template_name = "django_tables2/bootstrap5.html"
        attrs = {'class': 'table table-hover table-sm align-middle mb-0'}
