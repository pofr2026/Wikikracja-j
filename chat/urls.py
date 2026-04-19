# Third party imports
from django.urls import path

# Local folder imports
from . import push_api, views

app_name = 'chat'

urlpatterns = [
    path('', views.chat, name='chat'),
    path('add_room/', views.add_room, name='add_room'),
    path('upload/', views.upload_image),
    path('translations/', views.get_translations),

    # Push notification API endpoints
    path('api/push/register/', push_api.PushDeviceRegisterView.as_view(), name='push_register'),
    path('api/push/unregister/', push_api.PushDeviceUnregisterView.as_view(), name='push_unregister'),

    # Toggle notifications endpoint
    path('api/toggle-notifications/', views.toggle_notifications, name='toggle_notifications'),

    # Embedded chat widget API
    path('api/room/<int:room_id>/', views.room_data, name='room_data'),
]
