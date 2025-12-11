"""
URL configuration for kejebe project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_nested import routers

from apps.categories.views import CategoryViewSet
from apps.regions.views import RegionViewSet, CityViewSet
from apps.accounts.views import InboundSMSWebhookView, InitReverseSMSView, ConfirmReverseSMSView
from apps.services.views import ServiceViewSet, ReviewViewSet, FavoriteViewSet, ServiceProductViewSet, ServiceApplicationViewSet
from apps.stories.views import ServiceStoryViewSet
from apps.banners.views import BannerViewSet
from apps.home.views import HomeViewSet
from django.conf import settings
from django.conf.urls.static import static

router = routers.DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'cities', CityViewSet, basename='city')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'favorites', FavoriteViewSet, basename='favorite')
router.register(r'service-applications', ServiceApplicationViewSet, basename='service-application')
router.register(r'banners', BannerViewSet, basename='banner')
router.register(r'stories', ServiceStoryViewSet, basename='service-story')


services_router = routers.NestedDefaultRouter(router, r'services', lookup='service')
services_router.register(r'products', ServiceProductViewSet, basename='service-products')
services_router.register(r'stories', ServiceStoryViewSet, basename='service-stories')

api_patterns = [
    path('', include(router.urls)),
    path('', include(services_router.urls)),
    path('auth/', include('apps.users.urls')),
    path('devices/', include('apps.devices.urls')),
    path('home', HomeViewSet.as_view({'get': 'list'}), name='home'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_patterns)),
    path('api/v1/', include(api_patterns)),

    path("sms/inbound/", InboundSMSWebhookView.as_view(), name="sms-inbound"),
    path("auth/sms/init/", InitReverseSMSView.as_view(), name="auth-sms-init"),
    path("auth/sms/confirm/", ConfirmReverseSMSView.as_view(), name="auth-sms-confirm"),

    path('froala_editor/', include('froala_editor.urls'))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
