from django.urls import path
from . import views

urlpatterns = [
    path('client-details/<str:uuid>/', views.client_details, name='client_details'),
    path('client-details/', views.client_details, name='client_details'),  # Para adição de novo registro
    path('client-list/', views.client_list, name='client_list'),  # Rota para a lista de clientes
]