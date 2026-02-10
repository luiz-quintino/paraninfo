from django.urls import path
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.urls import include
from django.conf import settings
from .forms import CustomLoginForm

from django.conf.urls.static import static
from .views import CustomLoginView

urlpatterns = [
    # inclui as usls padrão do django
    # path('', include("django.contrib.auth.urls")),

    # Página de login
    path('login/', CustomLoginView.as_view(
            authentication_form=CustomLoginForm
            ), name='login'),
    
    # Página de logout
    path('logout/', LogoutView.as_view(), name='logout'),

    # Esqueci minha senha
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset.html'
    ), name='password_reset'),

    # Página de confirmação de envio do e-mail
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),

    # Página para redefinir a senha (link enviado por e-mail)
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html'
    ), name='password_reset_confirm'),

    # Página de sucesso após redefinir a senha
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),
]