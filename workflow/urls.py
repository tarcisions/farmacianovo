
from django.urls import path
from . import views

app_name = 'workflow'

urlpatterns = [
    # Etapas
    path('etapas/', views.lista_etapas, name='lista_etapas'),
    path('etapas/criar/', views.criar_etapa, name='criar_etapa'),
    path('etapas/<int:id>/editar/', views.editar_etapa, name='editar_etapa'),
    path('etapas/<int:id>/deletar/', views.deletar_etapa, name='deletar_etapa'),
    
    # Checklists por Etapa
    path('etapas/<int:etapa_id>/checklists/', views.checklists_etapa, name='checklists_etapa'),
    path('etapas/<int:etapa_id>/checklists/criar/', views.criar_checklist_etapa, name='criar_checklist_etapa'),
    
    # Checklists Gerais
    path('checklists/', views.lista_checklists, name='checklists'),
    path('checklists/<int:checklist_id>/editar/', views.editar_checklist, name='editar_checklist'),
    path('checklists/<int:checklist_id>/deletar/', views.deletar_checklist, name='deletar_checklist'),
]
