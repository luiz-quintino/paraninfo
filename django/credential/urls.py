from django.urls import path
from django.contrib import admin
from django.views.generic import TemplateView
from django.urls import include
from django.conf import settings

from django.conf.urls.static import static
from django.contrib.auth.views import LoginView
from .views import CustomLoginView

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('', include("django.contrib.auth.urls")),
    
]