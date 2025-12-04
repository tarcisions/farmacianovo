

from django.urls import path
from . import views
from . import views_scheduler
from . import views_perfil

app_name = 'core'

urlpatterns = [
    # Perfil do usuário
    path('meu-perfil/', views_perfil.meu_perfil, name='meu_perfil'),
    
    # Gerenciamento de usuários
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('usuarios/criar/', views.criar_usuario_view, name='criar_usuario'),
    path('usuarios/<int:user_id>/editar/', views.editar_usuario_view, name='editar_usuario'),
    path('usuarios/<int:user_id>/deletar/', views.deletar_usuario_view, name='deletar_usuario'),
    
    # Endpoints para scheduler (API)
    path('api/scheduler/status/', views_scheduler.status_scheduler, name='scheduler_status'),
    path('api/scheduler/iniciar/', views_scheduler.iniciar_scheduler, name='scheduler_iniciar'),
    path('api/scheduler/parar/', views_scheduler.parar_scheduler, name='scheduler_parar'),
    path('api/scheduler/sincronizar/', views_scheduler.sincronizar_agora, name='scheduler_sincronizar'),
]
