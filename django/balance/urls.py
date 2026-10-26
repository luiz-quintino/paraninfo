from django.views.generic import TemplateView
from django.urls import path
from . import views

app_name = "balance"

urlpatterns = [
    path("", views.balance_view, name="balance"), 
    path("balance-overview/", views.balance_overview, name="balance-overview"),
    path("reports/<int:report_id>/file/", views.balance_report_file, name="balance-report-file"),
    path("balance-my/<str:usuario>/", views.balance_my_view, name="balance_my"),
    path('get-extrato-details/<int:extrato_id>/', views.get_extrato_details, name='get_extrato_details'),
    path("fechar-balanco", views.close_balance_view, name="fechar_balanco"), 
    path("emitir-recibo", views.emitir_recibo_view, name="emitir_recibo"), 
    path("livro-caixa", views.livro_caixa, name="livro_caixa"), 
]   