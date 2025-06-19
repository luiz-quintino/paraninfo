from django.views.generic import TemplateView
from django.urls import path
from . import views
from users.views import user_credential

urlpatterns = [
    # path("", TemplateView.as_view(template_name="home.html"), name="home"),  # Rota para home.html
    path("", views.home_view, name="home"),  # Rota para home.html

]