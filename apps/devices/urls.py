from django.urls import path
from apps.devices.views import DeviceCityViewSet

device_city = DeviceCityViewSet.as_view({'post': 'create'})
device_info = DeviceCityViewSet.as_view({'get': 'retrieve_device'})

urlpatterns = [
    path('select-location/', device_city, name='device-select-location'),
    path('info/', device_info, name='device-info'),
]
