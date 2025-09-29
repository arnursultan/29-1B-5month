from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views as drf_authtoken_views
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api-auth/', include('rest_framework.urls')),

    path('api/auth/token/', drf_authtoken_views.obtain_auth_token, name='api-token'),

    path('api/', include('notes.urls')),
]

if settings.DEBUG:
    urlpatterns += [path('__debug__/', include('debug_toolbar.urls'))]
