from django.urls import path
from . import views

app_name = 'theaters'

urlpatterns = [
    path('', views.theater_list_view, name='list'),
    path('<int:theater_id>/', views.theater_detail_view, name='detail'),
]
