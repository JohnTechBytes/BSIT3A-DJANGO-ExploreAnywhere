from django.urls import path
from . import views

app_name = 'visits'

urlpatterns = [
    path('', views.my_visits, name='list'),
    path('check-in/<int:pk>/', views.check_in, name='check_in'),
]
