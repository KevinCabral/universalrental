"""core URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken.views import obtain_auth_token # <-- NEW
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI configuration
schema_view = get_schema_view(
   openapi.Info(
      title="SGA API",
      default_version='v1',
      description="Vehicle Rental Management System API",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@sga.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', include('apps.pages.urls')),
    path("", include("apps.dyn_dt.urls")),
    path("", include("apps.dyn_api.urls")),
    path('charts/', include('apps.charts.urls')),
    path('vehicle-rental/', include('apps.vehicle_rental.urls')),
    path("", include('admin_datta.urls')),
    path("admin/", admin.site.urls),
    
    # Authentication endpoints
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('vehicle-rental/api-token-auth/', obtain_auth_token, name='vehicle_rental_api_token_auth'),
    
    # Swagger/OpenAPI endpoints
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files during development (must be before other URL patterns)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Lazy-load on routing is needed
# During the first build, API is not yet generated
try:
    urlpatterns.append( path("api/"      , include("api.urls"))    )
    urlpatterns.append( path("login/jwt/", view=obtain_auth_token) )
except:
    pass
