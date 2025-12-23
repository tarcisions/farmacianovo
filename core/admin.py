from django.contrib import admin
from .models import (
    Etapa, Laboratorio, TipoProduto, PontuacaoPorAtividade,
    ConfiguracaoPontuacao, Checklist,
    Pedido, HistoricoEtapa, ChecklistExecucao,
    PontuacaoFuncionario, Penalizacao,
    PontuacaoFixaMensal, HistoricoAplicacaoPontuacaoFixa,
    BonusFaixa, HistoricoBonusMensal,
    ConfiguracaoExpedicao, RegistroExpedicao,
    LogAuditoria,
    ControlePergunta, ControlePerguntaOpcao, HistoricoControleQualidade, RespostaControleQualidade
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

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['id_api', 'id_pedido_api', 'id_pedido_web', 'nome_resumido', 'tipo', 'quantidade', 'status', 'etapa_atual', 'criado_em']
    list_filter = ['status', 'tipo', 'etapa_atual', 'tipo_identificado']
    search_fields = ['id_api', 'id_pedido_api', 'id_pedido_web', 'nome', 'descricao_web']
    date_hierarchy = 'criado_em'
    readonly_fields = ['id_api', 'id_pedido_api', 'id_pedido_web', 'descricao_web', 'price_unit', 'price_total', 'data_atualizacao_api', 'tipo_identificado', 'criado_em', 'atualizado_em']
    
    fieldsets = (
        ('IDs da API (Somente Leitura)', {
            'fields': ('id_api', 'id_pedido_api', 'id_pedido_web')
        }),
        ('Informações do Produto', {
            'fields': ('nome', 'descricao_web', 'tipo', 'quantidade')
        }),
        ('Preço', {
            'fields': ('price_unit', 'price_total')
        }),
        ('Fluxo', {
            'fields': ('etapa_atual', 'status', 'funcionario_na_etapa')
        }),
        ('Tipo Identificado', {
            'fields': ('tipo_identificado',)
        }),
        ('Histórico', {
            'fields': ('data_atualizacao_api', 'informacoes_gerais', 'criado_em', 'atualizado_em', 'concluido_em')
        }),
    )
    
    def nome_resumido(self, obj):
        return obj.nome[:50] if obj.nome else "N/A"
    nome_resumido.short_description = "Nome"

@admin.register(HistoricoEtapa)
class HistoricoEtapaAdmin(admin.ModelAdmin):
    list_display = ['pedido', 'etapa', 'funcionario', 'timestamp_inicio', 'timestamp_fim', 'pontos_gerados']
    list_filter = ['etapa', 'funcionario']
    search_fields = ['pedido__nome']
    date_hierarchy = 'timestamp_inicio'

@admin.register(ChecklistExecucao)
class ChecklistExecucaoAdmin(admin.ModelAdmin):
    list_display = ['checklist', 'historico_etapa', 'marcado', 'pontos_gerados']
    list_filter = ['marcado', 'checklist']

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

@admin.register(HistoricoAplicacaoPontuacaoFixa)
class HistoricoAplicacaoPontuacaoFixaAdmin(admin.ModelAdmin):
    list_display = ['regra', 'funcionario', 'mes_referencia', 'pontos_aplicados', 'aplicado_por']
    list_filter = ['regra', 'funcionario']
    date_hierarchy = 'aplicado_em'

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
    list_display = ['funcionario', 'configuracao', 'pedido', 'data', 'pontos_gerados']
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


@admin.register(ControlePergunta)
class ControlePerguntaAdmin(admin.ModelAdmin):
    list_display = ['pergunta', 'etapa', 'tipo_campo', 'ativo', 'obrigatorio', 'ordem']
    list_filter = ['etapa', 'tipo_campo', 'ativo', 'obrigatorio']
    search_fields = ['pergunta', 'descricao']
    ordering = ['etapa', 'ordem']
    inlines = [ControlePerguntaOpcaoInline]
    fieldsets = (
        ('Pergunta', {
            'fields': ('etapa', 'pergunta', 'tipo_campo', 'ordem')
        }),
        ('Configuração', {
            'fields': ('descricao', 'obrigatorio', 'ativo')
        }),
    )


@admin.register(ControlePerguntaOpcao)
class ControlePerguntaOpcaoAdmin(admin.ModelAdmin):
    list_display = ['texto_opcao', 'pergunta', 'ordem']
    list_filter = ['pergunta__etapa', 'pergunta']
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
    list_display = ['pedido', 'funcionario', 'preenchido_em', 'atualizado_em']
    list_filter = ['funcionario', 'preenchido_em']
    search_fields = ['pedido__nome', 'funcionario__username', 'pedido__codigo_pedido']
    date_hierarchy = 'preenchido_em'
    readonly_fields = ['pedido', 'funcionario', 'historico_etapa', 'preenchido_em', 'atualizado_em']
    inlines = [RespostaControleQualidadeInline]
    can_delete = False
    
    def has_add_permission(self, request):
        return False


@admin.register(RespostaControleQualidade)
class RespostaControleQualidadeAdmin(admin.ModelAdmin):
    list_display = ['pergunta', 'historico_controle', 'resposta_texto', 'resposta_opcao']
    list_filter = ['pergunta__etapa', 'pergunta']
    search_fields = ['historico_controle__pedido__nome', 'pergunta__pergunta']
    readonly_fields = ['pergunta', 'historico_controle', 'resposta_texto', 'resposta_opcao', 'preenchido_em']
    can_delete = False
    
    def has_add_permission(self, request):
        return False