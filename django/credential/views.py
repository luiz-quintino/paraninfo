from django.shortcuts import render
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.views import LoginView


def login_view(request):
    """
    Renderiza a página de login.
    """
    return render(request, "credential/login.html")

class CustomLoginView(LoginView):
    def get(self, request, *args, **kwargs):
        if 'next' in request.GET:
            messages.info(request, "Somente usuários autorizados")
        return super().get(request, *args, **kwargs)


