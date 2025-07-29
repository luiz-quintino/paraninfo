from django.views.generic import TemplateView
from django.urls import path
from . import views

urlpatterns = [
    path("", views.balance_view, name="balance"), 
    path("fechar-balanco", views.close_balance_view, name="fechar_balanco"), 
    path('get-extrato-details/<int:extrato_id>/', views.get_extrato_details, name='get_extrato_details')
]   