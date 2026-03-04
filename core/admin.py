from django.contrib import admin
from .models import (
    Etapa, Laboratorio, TipoProduto, PontuacaoPorAtividade,
    ConfiguracaoPontuacao, Checklist,
    PontuacaoFuncionario, Penalizacao,
    PontuacaoFixaMensal,
    BonusFaixa, HistoricoBonusMensal,
    ConfiguracaoExpedicao, RegistroExpedicao,
    LogAuditoria,
    ControlePergunta, ControlePerguntaOpcao, HistoricoControleQualidade, RespostaControleQualidade,
    ConfiguracaoControleQualidade,
    ConfiguracaoAPI, AgendamentoSincronizacao,
    PedidoMestre, FormulaItem, HistoricoEtapaFormula, ChecklistExecucaoFormula
)

@admin.register(Etapa)
class EtapaAdmin(admin.ModelAdmin):
    list_display = ['sequencia', 'nome', 'ativa', 'se_gera_pontos', 'pontos_fixos_etapa']
    list_filter = ['ativa']
    search_fields = ['nome']
    ordering = ['sequencia']

@admin.register(Laboratorio)
class LaboratorioAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'nome', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome']

@admin.register(TipoProduto)
class TipoProdutoAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'nome', 'laboratorio', 'ativo']
    list_filter = ['laboratorio', 'ativo']
    search_fields = ['nome']

@admin.register(PontuacaoPorAtividade)
class PontuacaoPorAtividadeAdmin(admin.ModelAdmin):
    list_display = ['etapa', 'tipo_produto', 'atividade', 'faixa_min', 'faixa_max', 'pontos_por_formula', 'ativo']
    list_filter = ['etapa', 'tipo_produto', 'atividade', 'ativo']
    search_fields = ['tipo_produto__nome']

@admin.register(ConfiguracaoPontuacao)
class ConfiguracaoPontuacaoAdmin(admin.ModelAdmin):
    list_display = ['etapa', 'versao', 'pontos_fixos', 'ativa']
    list_filter = ['ativa']
    search_fields = ['etapa__nome']

@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = ['nome', 'etapa', 'pontos_do_check', 'obrigatorio', 'ativo']
    list_filter = ['etapa', 'obrigatorio', 'ativo']
    search_fields = ['nome', 'descricao']

@admin.register(PontuacaoFuncionario)
class PontuacaoFuncionarioAdmin(admin.ModelAdmin):
    list_display = ['funcionario', 'pontos', 'origem', 'timestamp', 'mes_referencia']
    list_filter = ['origem', 'funcionario']
    search_fields = ['funcionario__username']
    date_hierarchy = 'timestamp'

@admin.register(Penalizacao)
class PenalizacaoAdmin(admin.ModelAdmin):
    list_display = ['funcionario', 'pontos', 'motivo', 'aplicada_por', 'timestamp', 'revertida']
    list_filter = ['revertida', 'aplicada_por']
    search_fields = ['funcionario__username', 'motivo']
    date_hierarchy = 'timestamp'

@admin.register(PontuacaoFixaMensal)
class PontuacaoFixaMensalAdmin(admin.ModelAdmin):
    list_display = ['nome_regra', 'valor', 'tipo_aplicacao', 'ativa']
    list_filter = ['tipo_aplicacao', 'ativa']
    search_fields = ['nome_regra']

@admin.register(BonusFaixa)
class BonusFaixaAdmin(admin.ModelAdmin):
    list_display = ['faixa_min', 'faixa_max', 'valor_em_reais', 'ativo']
    list_filter = ['ativo']
    ordering = ['faixa_min']

@admin.register(HistoricoBonusMensal)
class HistoricoBonusMensalAdmin(admin.ModelAdmin):
    list_display = ['funcionario', 'mes_referencia', 'pontos_totais_mes', 'valor_em_reais_calculado', 'status_pagamento']
    list_filter = ['status_pagamento', 'mes_referencia']
    search_fields = ['funcionario__username']
    date_hierarchy = 'mes_referencia'

@admin.register(ConfiguracaoExpedicao)
class ConfiguracaoExpedicaoAdmin(admin.ModelAdmin):
    list_display = ['tipo_expedicao', 'pontos_por_rota_motoboy', 'tipo_pontuacao_sedex', 'ativo']
    list_filter = ['tipo_expedicao', 'ativo']

@admin.register(RegistroExpedicao)
class RegistroExpedicaoAdmin(admin.ModelAdmin):
    list_display = ['funcionario', 'configuracao', 'data', 'pontos_gerados']
    list_filter = ['configuracao', 'funcionario']
    search_fields = ['funcionario__username']
    date_hierarchy = 'data'

@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'acao', 'descricao', 'timestamp', 'ip_address']
    list_filter = ['acao', 'usuario']
    search_fields = ['usuario__username', 'descricao']
    date_hierarchy = 'timestamp'
    readonly_fields = ['usuario', 'acao', 'descricao', 'timestamp', 'ip_address', 'dados_adicionais']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

class ControlePerguntaOpcaoInline(admin.TabularInline):
    model = ControlePerguntaOpcao
    extra = 1
    fields = ['texto_opcao', 'ordem']
    ordering = ['ordem']


@admin.register(ConfiguracaoControleQualidade)
class ConfiguracaoControleQualidadeAdmin(admin.ModelAdmin):
    list_display = ['nome_configuracao', 'pontos_por_formulario', 'ativa', 'criado_em']
    list_filter = ['ativa']
    search_fields = ['nome_configuracao']
    readonly_fields = ['criado_em', 'atualizado_em']
    fieldsets = (
        ('Configuração', {
            'fields': ('nome_configuracao', 'pontos_por_formulario', 'ativa')
        }),
        ('Descrição', {
            'fields': ('descricao',),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ControlePergunta)
class ControlePerguntaAdmin(admin.ModelAdmin):
    list_display = ['pergunta', 'tipo_campo', 'ativo', 'obrigatorio', 'ordem']
    list_filter = ['tipo_campo', 'ativo', 'obrigatorio']
    search_fields = ['pergunta', 'descricao']
    ordering = ['ordem']
    inlines = [ControlePerguntaOpcaoInline]
    fieldsets = (
        ('Pergunta', {
            'fields': ('pergunta', 'tipo_campo', 'ordem')
        }),
        ('Configuração', {
            'fields': ('descricao', 'obrigatorio', 'ativo')
        }),
    )


@admin.register(ControlePerguntaOpcao)
class ControlePerguntaOpcaoAdmin(admin.ModelAdmin):
    list_display = ['texto_opcao', 'pergunta', 'ordem']
    list_filter = ['pergunta']
    search_fields = ['texto_opcao', 'pergunta__pergunta']
    ordering = ['pergunta', 'ordem']


class RespostaControleQualidadeInline(admin.TabularInline):
    model = RespostaControleQualidade
    extra = 0
    readonly_fields = ['pergunta', 'resposta_texto', 'resposta_opcao', 'preenchido_em']
    can_delete = False
    fields = ['pergunta', 'resposta_texto', 'resposta_opcao']


@admin.register(HistoricoControleQualidade)
class HistoricoControleQualidadeAdmin(admin.ModelAdmin):
    list_display = ['id_controle', 'nome_item', 'funcionario', 'pontuacao', 'preenchido_em']
    list_filter = ['funcionario', 'preenchido_em']
    search_fields = ['id_controle', 'nome_item', 'codigo_item', 'funcionario__username']
    date_hierarchy = 'preenchido_em'
    readonly_fields = ['funcionario', 'preenchido_em', 'atualizado_em']
    inlines = [RespostaControleQualidadeInline]
    can_delete = False
    fieldsets = (
        ('Informações do Item', {
            'fields': ('id_controle', 'nome_item', 'codigo_item')
        }),
        ('Sistema', {
            'fields': ('funcionario', 'pontuacao', 'preenchido_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False


@admin.register(RespostaControleQualidade)
class RespostaControleQualidadeAdmin(admin.ModelAdmin):
    list_display = ['pergunta', 'historico_controle', 'resposta_texto', 'resposta_opcao']
    list_filter = ['pergunta']
    search_fields = ['historico_controle__nome_item', 'pergunta__pergunta']
    readonly_fields = ['pergunta', 'historico_controle', 'resposta_texto', 'resposta_opcao', 'preenchido_em']
    can_delete = False
    
    def has_add_permission(self, request):
        return False


@admin.register(ConfiguracaoAPI)
class ConfiguracaoAPIAdmin(admin.ModelAdmin):
    list_display = ['nome', 'url_base', 'tipo_autenticacao', 'ativa', 'atualizado_em']
    list_filter = ['tipo_autenticacao', 'ativa']
    search_fields = ['nome', 'url_base', 'descricao']
    readonly_fields = ['criado_em', 'atualizado_em']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'url_base', 'descricao', 'ativa')
        }),
        ('Autenticação', {
            'fields': ('tipo_autenticacao', 'bearer_token', 'api_key', 'usuario', 'senha', 'headers_customizados')
        }),
        ('Configurações', {
            'fields': ('timeout', 'criado_em', 'atualizado_em')
        }),
    )


@admin.register(AgendamentoSincronizacao)
class AgendamentoSincronizacaoAdmin(admin.ModelAdmin):
    list_display = ['api', 'nome', 'horario_execucao', 'ativo', 'atualizado_em']
    list_filter = ['api', 'ativo', 'executar_todos_os_dias']
    search_fields = ['api__nome', 'nome', 'descricao']
    readonly_fields = ['criado_em', 'atualizado_em']
    actions = ['recarregar_scheduler', 'sincronizar_agora']
    
    fieldsets = (
        ('API e Agendamento', {
            'fields': ('api', 'nome', 'descricao')
        }),
        ('Dias de Execução', {
            'fields': ('executar_todos_os_dias', 'dias_semana')
        }),
        ('Horário', {
            'fields': ('horario_execucao',)
        }),
        ('Paginações', {
            'fields': ('paginacoes',),
            'description': 'Lista de dicts: [{"pagina": 1, "tamanho": 50}]'
        }),
        ('Status', {
            'fields': ('ativo', 'criado_em', 'atualizado_em')
        }),
    )
    
    def recarregar_scheduler(self, request, queryset):
        """Recarrega o scheduler para ativar mudanças nos agendamentos"""
        try:
            from core.scheduler import AgendadorSincronizacao
            AgendadorSincronizacao.recarregar_agendamentos()
            self.message_user(request, "[OK] Scheduler recarregado com sucesso! Novos agendamentos estao em vigor.")
        except Exception as e:
            self.message_user(request, f"[ERRO] Falha ao recarregar scheduler: {str(e)}", level=admin.messages.ERROR)
    recarregar_scheduler.short_description = "[>>] Recarregar scheduler com novos agendamentos"
    
    def sincronizar_agora(self, request, queryset):
        """Sincroniza imediatamente os agendamentos selecionados"""
        try:
            from core.scheduler import AgendadorSincronizacao
            for agendamento in queryset:
                AgendadorSincronizacao.sincronizar_agora(agendamento.id)
            self.message_user(request, f"[OK] Sincronizacao iniciada para {queryset.count()} agendamento(s)!")
        except Exception as e:
            self.message_user(request, f"[ERRO] Falha na sincronizacao: {str(e)}", level=admin.messages.ERROR)
    sincronizar_agora.short_description = "[>>] Sincronizar agora"


# ========== ADMIN PARA NOVOS MODELOS ==========

@admin.register(PedidoMestre)
class PedidoMestreAdmin(admin.ModelAdmin):
    list_display = ['nrorc', 'status', 'total_formulas', 'formulas_prontas', 'criado_em']
    list_filter = ['status', 'criado_em']
    search_fields = ['nrorc']
    readonly_fields = ['criado_em', 'atualizado_em', 'concluido_em', 'total_formulas', 'formulas_prontas']
    
    fieldsets = (
        ('Informacoes Basicas', {
            'fields': ('nrorc', 'status')
        }),
        ('Formulas', {
            'fields': ('total_formulas', 'formulas_prontas')
        }),
        ('Observacoes', {
            'fields': ('observacoes',)
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em', 'concluido_em')
        }),
    )


@admin.register(FormulaItem)
class FormulaItemAdmin(admin.ModelAdmin):
    list_display = ['pedido_mestre', 'status', 'etapa_atual', 'funcionario_na_etapa', 'criado_em', 'datetime_atualizacao_api']
    list_filter = ['status', 'etapa_atual', 'criado_em', 'datetime_atualizacao_api']
    search_fields = ['pedido_mestre__nrorc', 'descricao', 'id_api']
    readonly_fields = ['criado_em', 'atualizado_em', 'concluido_em', 'id_api', 'datetime_atualizacao_api']
    
    fieldsets = (
        ('Pedido e Formula', {
            'fields': ('pedido_mestre', 'descricao', 'volume_ml', 'quantidade')
        }),
        ('Dados da API', {
            'fields': ('id_api', 'serieo', 'price_unit', 'price_total', 'data_criacao_api', 'data_atualizacao_api', 'datetime_atualizacao_api')
        }),
        ('Status e Fluxo', {
            'fields': ('status', 'etapa_atual', 'funcionario_na_etapa')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em', 'concluido_em')
        }),
    )


@admin.register(HistoricoEtapaFormula)
class HistoricoEtapaFormulaAdmin(admin.ModelAdmin):
    list_display = ['formula', 'etapa', 'funcionario', 'timestamp_inicio', 'tempo_gasto_minutos', 'pontos_gerados']
    list_filter = ['etapa', 'timestamp_inicio']
    search_fields = ['formula__pedido_mestre__nrorc', 'funcionario__username']
    readonly_fields = ['timestamp_inicio', 'tempo_gasto_formatado', 'tempo_gasto_minutos']
    
    fieldsets = (
        ('Formula e Etapa', {
            'fields': ('formula', 'etapa', 'funcionario')
        }),
        ('Timeline', {
            'fields': ('timestamp_inicio', 'timestamp_fim', 'tempo_gasto_formatado', 'tempo_gasto_minutos')
        }),
        ('Pontuacao e Outros', {
            'fields': ('pontos_gerados', 'rota_tipo', 'observacoes')
        }),
    )


@admin.register(ChecklistExecucaoFormula)
class ChecklistExecucaoFormulaAdmin(admin.ModelAdmin):
    list_display = ['checklist', 'historico_etapa', 'marcado', 'pontos_gerados', 'marcado_em']
    list_filter = ['historico_etapa__etapa', 'marcado']
    search_fields = ['checklist__nome', 'historico_etapa__formula__pedido_mestre__nrorc']
    readonly_fields = ['marcado_em']
    
    fieldsets = (
        ('Checklist', {
            'fields': ('historico_etapa', 'checklist')
        }),
        ('Status e Pontos', {
            'fields': ('marcado', 'pontos_gerados', 'marcado_em')
        }),
    )