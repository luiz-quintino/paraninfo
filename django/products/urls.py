from django.urls import path

from . import views


app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='products'),
    path('product-list/', views.product_list, name='product_list'),
    path('product-list/<str:UUID>/', views.product_list, name='product_list'),
    path('product-my-list/<str:UUID>/', views.product_my_list, name='product_my_list'),
    path('product-edit/<int:product_id>/', views.product_edit, name='product_edit'),
    path('product-edit/', views.product_edit, name='product_edit'),
    path('product-approval/', views.product_approval, name='product_approval'),
]