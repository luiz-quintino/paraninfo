from django.urls import path

from . import views

urlpatterns = [
    path('', views.email, name='email'),
    path('email/', views.email, name='email_legacy'),
    path('email-list/', views.email_list, name='email_list'),
    path('email-list/<int:email_id>/detail/', views.email_detail, name='email_detail'),
]
