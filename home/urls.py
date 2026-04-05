# Third party imports
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

# Local folder imports
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('mark-as-read/', views.mark_as_read, name='mark_as_read'),
    path('mark-unread/', views.mark_unread, name='mark_unread'),

    # not in use at this point. Contact through https://wikikracja.pl/kontakt/
    # path('contact/', TemplateView.as_view(template_name="home/contact.html"), name='contact'),

    # reset password
    # https://simpleisbetterthancomplex.com/tutorial/2016/09/19/how-to-create-password-reset-view.html
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='home/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='home/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='home/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='home/password_reset_complete.html'), name='password_reset_complete'),

    # for generating dynamic manifest content
    path('manifest.json', views.manifest, name='manifest'),

    # Service Worker - serve with correct MIME type
    path('sw.js', views.service_worker, name='service_worker'),
]
