from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('ooda_app.urls')),
    path('api/auth/', include('django.contrib.auth.urls')),
]
