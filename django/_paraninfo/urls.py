from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path
from django.urls import include

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    # Rota para home projeto Django
    path("", include("home.urls")),  # Inclui as URLs do app home
    path('admin/', admin.site.urls),  # Acessar o admin do Django
    path("credential/", include("credential.urls")),  # Inclui as URLs do app credential
    path('users/', include('users.urls')),  # Inclui o app users
    path('email/', include('email_app.urls')),  # Inclui o app email_app  # Inclui as URLs do app users
    path('paraninfo-admin/', include('paraninfo_admin.urls')),  # Inclui as URLs do app users
    path('transaction/', include('transaction.urls')),  # Inclui as URLs do app users
    path('balance/', include('balance.urls', namespace='balance')),  # Inclui as URLs do app contabilidade
    path('products/', include('products.urls')),

]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
