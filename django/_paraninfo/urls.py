from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path
from django.urls import include

from django.conf import settings


from django.conf.urls.static import static

urlpatterns = [
    # Rota para home projeto Django
    path("", include("home.urls")),  # Inclui as URLs do app home
    path('admin/', admin.site.urls),  # Acessar o admin do Django
    path("credential/", include("credential.urls")),  # Inclui as URLs do app credential
    path('users/', include('users.urls')),  # Inclui as URLs do app users
    path('paraninfo-admin/', include('paraninfo_admin.urls')),  # Inclui as URLs do app users

]
