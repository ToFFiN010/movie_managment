from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('write/<int:movie_id>/', views.create_review_view, name='write_review'),
    path('report/<int:review_id>/', views.report_review_view, name='report_review'),
]
