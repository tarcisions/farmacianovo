
from django.urls import path
from . import views

app_name = 'workflow'

urlpatterns = [
    path('etapas/', views.lista_etapas, name='etapas'),
    path('checklists/', views.lista_checklists, name='checklists'),
]
