from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('funcionario/', views.dashboard_funcionario, name='funcionario'),
    path('gerente/', views.dashboard_gerente, name='gerente'),
    path('superadmin/', views.dashboard_superadmin, name='superadmin'),
    path('pedidos/', views.lista_pedidos, name='pedidos'),
    
    # URLs de funcionário
    path('meus-pedidos/', views.meus_pedidos_funcionario, name='meus_pedidos'),
    path('pedidos-disponiveis/', views.pedidos_disponiveis_funcionario, name='pedidos_disponiveis'),
    path('assumir-pedido/<int:pedido_id>/', views.assumir_pedido, name='assumir_pedido'),
    path('trabalhar-pedido/<int:pedido_id>/', views.trabalhar_pedido, name='trabalhar_pedido'),
    path('selecionar-rota/<int:pedido_id>/<str:tipo_rota>/', views.selecionar_rota_expedicao, name='selecionar_rota'),
    path('toggle-status-fila/<int:pedido_id>/', views.toggle_status_fila, name='toggle_status_fila'),
    path('marcar-checklist/<int:execucao_id>/', views.marcar_checklist, name='marcar_checklist'),
    path('concluir-etapa/<int:pedido_id>/', views.concluir_etapa, name='concluir_etapa'),
    path('expedicao-motoboy/', views.expedicao_motoboy, name='expedicao_motoboy'),
    path('expedicao-sedex/', views.expedicao_sedex, name='expedicao_sedex'),

    # Rotas finalizadas (expedição)
    path('rotas-finalizadas/', views.rotas_finalizadas_funcionario, name='rotas_finalizadas'),
    path('rotas-finalizadas/<int:historico_id>/', views.detalhe_rota_finalizada, name='detalhe_rota_finalizada'),
    path('rotas-finalizadas/gerente/', views.rotas_finalizadas_gerente, name='rotas_finalizadas_gerente'),
    
    # Histórico de etapas e pedidos concluídos
    path('historico-etapas/', views.historico_etapas_funcionario, name='historico_etapas'),
    path('pedidos-concluidos/', views.pedidos_concluidos, name='pedidos_concluidos'),
    
    # Controle de Qualidade
    path('controle-qualidade/<int:pedido_id>/', views.controle_qualidade, name='controle_qualidade'),
    path('historico-controle-qualidade/<int:pedido_id>/', views.historico_controle_qualidade, name='historico_controle_qualidade'),
    path('controle-qualidade/', views.controle_qualidade_lista, name='controle_qualidade_lista'),
    
    # Perfil e lista de funcionários
    path('perfil-funcionario/', views.perfil_funcionario, name='perfil_funcionario'),
    path('perfil-funcionario/<int:user_id>/', views.perfil_funcionario, name='perfil_funcionario_outro'),
    path('funcionarios/', views.lista_funcionarios, name='lista_funcionarios'),
    
    # Exportação de relatórios
    path('exportar-relatorio-gerente/', views.exportar_relatorio_gerente, name='exportar_relatorio_gerente'),
    path('exportar-relatorio-superadmin/', views.exportar_relatorio_superadmin, name='exportar_relatorio_superadmin'),
    
    # Penalizações
    path('penalizacoes/', views.penalizacoes_view, name='penalizacoes'),
    path('penalizacoes/criar/', views.criar_penalizacao, name='criar_penalizacao'),
    path('penalizacoes/reverter/<int:penalizacao_id>/', views.reverter_penalizacao, name='reverter_penalizacao'),
    
    # Auditoria
    path('auditoria/', views.auditoria, name='auditoria'),
]
