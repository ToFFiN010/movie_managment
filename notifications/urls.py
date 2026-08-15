from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list_view, name='list'),
    path('mark-read/<int:pk>/', views.mark_read_view, name='mark_read'),
    path('mark-all-read/', views.mark_all_read_view, name='mark_all_read'),
]
