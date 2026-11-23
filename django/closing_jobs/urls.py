from django.urls import path

from . import views

app_name = 'closing_jobs'

urlpatterns = [
    path('<int:job_id>/status/', views.job_status, name='status'),
]
