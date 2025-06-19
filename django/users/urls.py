from django.urls import path
from . import views
from users.views import user_credential

urlpatterns = [
    path('user-list/', views.user_list, name='user_list'),
    path('user-record/<str:uuid>/', views.user_record, name='user_record'),  
    path('user-record/', views.user_record, name='user_record'),  
    path('user-credential/<uuid:uuid>/', user_credential, name='user_credential'),


]