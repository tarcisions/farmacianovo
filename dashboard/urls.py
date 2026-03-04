from django.urls import path
from . import views, views_formulas

app_name = 'dashboard'

urlpatterns = [
    # ============ DASHBOARDS ============
    path('', views.home, name='home'),
    path('funcionario/', views.dashboard_funcionario, name='funcionario'),
    path('gerente/', views.dashboard_gerente, name='gerente'),
    path('superadmin/', views.dashboard_superadmin, name='superadmin'),
    
    # ============ LISTA DE PEDIDOS MESTRES ============
    path('pedidos/', views.lista_pedidos, name='pedidos'),
    
    # ============ NOVO FLUXO COM MÚLTIPLAS FÓRMULAS ============
    # Fórmulas disponíveis e trabalho do funcionário
    path('formulas-disponiveis/', views_formulas.formulas_disponiveis, name='formulas_disponiveis'),
    path('minhas-formulas/', views_formulas.minhas_formulas, name='minhas_formulas'),
    path('assumir-formula/<int:formula_id>/', views_formulas.assumir_formula, name='assumir_formula'),
    path('pausar-tarefa/<int:formula_id>/', views_formulas.pausar_tarefa_formula, name='pausar_tarefa'),
    path('ativar-tarefa/<int:formula_id>/', views_formulas.ativar_tarefa_formula, name='ativar_tarefa'),
    path('formula/<int:formula_id>/', views_formulas.detalhe_formula, name='detalhe_formula'),
    path('formula/<int:formula_id>/historico/', views_formulas.historico_etapas_formula, name='historico_etapas'),
    path('formula/<int:formula_id>/marcar-checklist/<int:checklist_id>/', views_formulas.marcar_checklist_formula, name='marcar_checklist_formula'),
    path('formula/<int:formula_id>/finalizar/', views_formulas.finalizar_etapa_formula, name='finalizar_etapa_formula'),
    
    # Expedição (Rotas Unificadas)
    path('pedido/<int:pedido_id>/escolher-rota/<str:rota_tipo>/', views_formulas.pedido_escolher_rota, name='pedido_escolher_rota'),
    path('rotas/', views_formulas.rotas_unificada, name='rotas_unificada'),
    path('rotas/finalizar/<str:rota_tipo>/', views_formulas.finalizar_rota, name='finalizar_rota'),
    path('rotas/expedicao/<int:expedicao_id>/', views_formulas.expedicao_detalhes, name='expedicao_detalhes'),
    
    # ============ TRANSPARENTE - OUTRAS FUNCIONALIDADES ============
    # Controle de Qualidade
    path('controle-qualidade/', views.controle_qualidade, name='controle_qualidade'),
    path('controle-qualidade/novo/', views.controle_qualidade_formulario, name='controle_qualidade_novo'),
    path('controle-qualidade/<int:formulario_id>/', views.controle_qualidade_detalhe, name='controle_qualidade_detalhe'),
    
    # Funcionários e Perfis
    path('perfil-funcionario/<int:user_id>/', views.perfil_funcionario, name='perfil_funcionario_outro'),
    path('funcionarios/', views.lista_funcionarios, name='lista_funcionarios'),
    
    # Relatórios e Exportação
    path('exportar-relatorio-gerente/', views.exportar_relatorio_gerente, name='exportar_relatorio_gerente'),
    path('exportar-relatorio-superadmin/', views.exportar_relatorio_superadmin, name='exportar_relatorio_superadmin'),
    
    # Penalizações
    path('penalizacoes/', views.penalizacoes_view, name='penalizacoes'),
    path('penalizacoes/criar/', views.criar_penalizacao, name='criar_penalizacao'),
    path('penalizacoes/reverter/<int:penalizacao_id>/', views.reverter_penalizacao, name='reverter_penalizacao'),
    
    # Auditoria
    path('auditoria/', views.auditoria, name='auditoria'),
]

