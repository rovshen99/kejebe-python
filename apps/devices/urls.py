from django.urls import path
from apps.devices.views import DeviceCityViewSet

device_city = DeviceCityViewSet.as_view({'post': 'create'})

urlpatterns = [
    path('select-city/', device_city, name='device-select-city'),
]
