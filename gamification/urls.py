
from django.urls import path
from . import views

app_name = 'gamification'

urlpatterns = [
    path('pontuacao/', views.pontuacao_view, name='pontuacao'),
    path('bonus/', views.bonus_view, name='bonus'),
]
