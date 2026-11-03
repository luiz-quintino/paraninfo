from django.views.generic import TemplateView
from django.urls import path
from . import views

app_name = "certificate"

urlpatterns = [
    path("", views.certificate, name="certificate"), 

]   