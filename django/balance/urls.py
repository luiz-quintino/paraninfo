from django.views.generic import TemplateView
from django.urls import path
from . import views

urlpatterns = [
    # path("", TemplateView.as_view(template_name="home.html"), name="home"),  # Rota para home.html
    path("", views.balance_view, name="balance"),  # Rota para home.html

]