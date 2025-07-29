from django.views.generic import TemplateView
from django.urls import path
from . import views

urlpatterns = [
    # path("", TemplateView.as_view(template_name="home.html"), name="home"),  # Rota para home.html
    path("", views.transaction_view, name="transaction"),  # Rota para home.html
    path('aceitar-extrato/', views.aceitar_extrato, name='aceitar_extrato'),        # lê extrato
    path('importacao/', views.importacao_view, name='importacao'),                  # importa extrato e trata dados duplicados
    
    path("extrato-config", views.extrato_config, name="extrato_config"),            # configurações de entrada de extrato
    path("entrada-manual", views.entrada_manual_view, name="entrada_manual"),       # configurações de entrada de extrato
    path("analise-movimentacao", views.analise_movimentacao_view, name="analise_movimentacao"),             # configurações de entrada de extrato
    path("edit-extrato", views.edit_extrato_view, name="edit_extrato"),             # configurações de entrada de extrato
    
    path("get-extrato-details/<int:extrato_id>/", views.get_extrato_details, name='get_extrato_details'),
]