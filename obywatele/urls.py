# Third party imports
from django.contrib.auth.decorators import login_required
from django.urls import path

# First party imports
from obywatele import views as v

app_name = 'obywatele'

urlpatterns = (
    path('', v.obywatele, name='obywatele'),
    path('onboarding/', v.onboarding_details, name='onboarding_details'),
    path('onboarding/waiting/', v.onboarding_waiting, name='onboarding_waiting'),
    path('poczekalnia/', v.poczekalnia, name='poczekalnia'),
    path('poczekalnia/<int:pk>/', v.obywatele_szczegoly, name='poczekalnia_szczegoly'),
    path('<int:pk>/', v.obywatele_szczegoly, name='obywatele_szczegoly'),
    path('my_profile/', v.my_profile, name='my_profile'),
    path('my_profile/avatar/', v.upload_avatar, name='upload_avatar'),
    path('my_profile/language/', v.set_user_language, name='set_language'),
    path('toggle_notification/', v.toggle_notification, name='toggle_notification'),
    path('my_assets/', v.my_assets, name='my_assets'),
    path('nowy/', v.dodaj, name='zaproponuj_osobe'),
    path('change_username/', v.change_username, name='change_username'),
    path("assets/", login_required(v.AssetListView.as_view()), name='assets'),
    path('parameters/', v.parameters, name='parameters'),
    path('wspolnota/', v.wspolnota, name='wspolnota'),
)
