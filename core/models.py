from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal

class Etapa(models.Model):
    nome = models.CharField(max_length=200)
    sequencia = models.IntegerField()
    ativa = models.BooleanField(default=True)
    se_gera_pontos = models.BooleanField(default=True)
    se_possui_checklists = models.BooleanField(default=False)
    se_possui_calculo_por_quantidade = models.BooleanField(default=False)
    pontos_fixos_etapa = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text='Pontos adicionados ao concluir a etapa (além dos checklists, se houver)'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sequencia']
        verbose_name = 'Etapa'
        verbose_name_plural = 'Etapas'
    
    def __str__(self):
        return f"{self.sequencia}. {self.nome}"
    
    def clean(self):
        if self.sequencia < 0:
            raise ValidationError('A sequência não pode ser negativa.')
    
    def proxima_etapa(self):
        return Etapa.objects.filter(sequencia__gt=self.sequencia, ativa=True).first()


class Laboratorio(models.Model):
    """Laboratórios dentro da etapa de Produção"""
    TIPOS_LABORATORIO = [
        ('capsula_sache', 'Laboratório de Cápsulas e Sachês'),
        ('pediatrico', 'Laboratório Pediátrico'),
        ('externo', 'Laboratório Externo'),
    ]
    
    tipo = models.CharField(max_length=50, choices=TIPOS_LABORATORIO, unique=True)
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Laboratório'
        verbose_name_plural = 'Laboratórios'
    
    def __str__(self):
        return self.nome




class TipoProduto(models.Model):
    """Define os tipos de produtos e suas características"""
    TIPOS = [
        ('capsula', 'Cápsula'),
        ('sache', 'Sachê'),
        ('liquido_pediatrico', 'Líquido Pediátrico'),
        ('lotion', 'Loção'),
        ('creme', 'Creme'),
        ('shampoo', 'Shampoo'),
        ('shot', 'Shot'),
        ('ovulo', 'Óvulo'),
        ('comprimido_sublingual', 'Comprimido Sublingual'),
        ('capsula_oleosa', 'Cápsula Oleosa'),
        ('goma', 'Goma'),
        ('chocolate', 'Chocolate'),
        ('filme', 'Filme'),
    ]
    
    tipo = models.CharField(max_length=50, choices=TIPOS, unique=True)
    nome = models.CharField(max_length=200)
    laboratorio = models.ForeignKey(Laboratorio, on_delete=models.CASCADE, related_name='tipos_produtos', null=True, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Tipo de Produto'
        verbose_name_plural = 'Tipos de Produto'
    
    def __str__(self):
        return self.nome


class PontuacaoPorAtividade(models.Model):
    """
    Define as pontuações por atividade e quantidade.
    Exemplo: Capsula Encapsulação de 0-60: 1 ponto
    """
    ATIVIDADES = [
        ('pesagem', 'Pesagem'),
        ('encapsulacao', 'Encapsulação'),
        ('analise', 'Análise'),
        ('rotulagem', 'Rotulagem'),
        ('conferencia', 'Conferência'),
        ('reconferencia', 'Reconferência'),
    ]
    
    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, related_name='pontuacoes_atividade')
    tipo_produto = models.ForeignKey(TipoProduto, on_delete=models.CASCADE, related_name='pontuacoes', null=True, blank=True)
    atividade = models.CharField(max_length=50, choices=ATIVIDADES)
    faixa_min = models.IntegerField()  # Quantidade mínima
    faixa_max = models.IntegerField()  # Quantidade máxima
    pontos_por_formula = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['etapa', 'tipo_produto', 'atividade', 'faixa_min']
        verbose_name = 'Pontuação por Atividade'
        verbose_name_plural = 'Pontuações por Atividade'
        unique_together = ['etapa', 'tipo_produto', 'atividade', 'faixa_min', 'faixa_max']
    
    def __str__(self):
        tipo_str = f" - {self.tipo_produto.nome}" if self.tipo_produto else ""
        return f"{self.etapa.nome} - {self.atividade}{tipo_str} ({self.faixa_min}-{self.faixa_max}): {self.pontos_por_formula} pts"
    
    @classmethod
    def calcular_pontos(cls, etapa, atividade, tipo_produto, quantidade):
        """Calcula a pontuação baseado na quantidade"""
        regra = cls.objects.filter(
            etapa=etapa,
            atividade=atividade,
            tipo_produto=tipo_produto,
            faixa_min__lte=quantidade,
            faixa_max__gte=quantidade,
            ativo=True
        ).first()
        
        if regra:
            return regra.pontos_por_formula
        return Decimal('0')


class ConfiguracaoPontuacao(models.Model):
    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, related_name='configuracoes_pontuacao')
    pontos_fixos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pontos_por_check = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pontos_min = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pontos_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ativa = models.BooleanField(default=True)
    versao = models.CharField(max_length=20, default='1.0')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-versao']
        verbose_name = 'Configuração de Pontuação'
        verbose_name_plural = 'Configurações de Pontuação'
    
    def __str__(self):
        return f"{self.etapa.nome} - v{self.versao}"
    
    @classmethod
    def get_versao_ativa(cls, etapa):
        return cls.objects.filter(etapa=etapa, ativa=True).order_by('-versao').first()


class Checklist(models.Model):
    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, related_name='checklists')
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    pontos_do_check = models.DecimalField(max_digits=10, decimal_places=2)
    obrigatorio = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['ordem', 'id']
        verbose_name = 'Checklist'
        verbose_name_plural = 'Checklists'
    
    def __str__(self):
        return f"{self.etapa.nome} - {self.nome}"



class PontuacaoFuncionario(models.Model):
    ORIGEM_CHOICES = [
        ('etapa', 'Etapa'),
        ('producao', 'Produção'),
        ('check', 'Checklist'),
        ('penalizacao', 'Penalização'),
        ('expedicao', 'Expedição'),
        ('mensal', 'Bonificação Mensal'),
        ('controle_qualidade', 'Controle de Qualidade'),
    ]
    
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pontuacoes')
    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, null=True, blank=True)
    pontos = models.DecimalField(max_digits=10, decimal_places=2)
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    mes_referencia = models.DateField()
    observacao = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Pontuação do Funcionário'
        verbose_name_plural = 'Pontuações dos Funcionários'
    
    def __str__(self):
        return f"{self.funcionario.username} - {self.pontos} pts ({self.origem})"
    
    @classmethod
    def pontos_mes_atual(cls, funcionario):
        hoje = timezone.now().date()
        primeiro_dia = hoje.replace(day=1)
        return cls.objects.filter(
            funcionario=funcionario,
            mes_referencia__gte=primeiro_dia,
            mes_referencia__lte=hoje
        ).aggregate(total=models.Sum('pontos'))['total'] or Decimal('0')


class Penalizacao(models.Model):
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='penalizacoes')
    motivo = models.CharField(max_length=500)
    pontos = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    justificativa = models.TextField()
    revertida = models.BooleanField(default=False)
    revertida_em = models.DateTimeField(null=True, blank=True)
    revertida_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='penalizacoes_revertidas')
    aplicada_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='penalizacoes_aplicadas')
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Penalização'
        verbose_name_plural = 'Penalizações'
    
    def __str__(self):
        status = '(REVERTIDA)' if self.revertida else ''
        return f"{self.funcionario.username} - {self.pontos} pts {status}"


class PontuacaoFixaMensal(models.Model):
    """
    Pontuações fixas mensais como:
    - 200 pontos por organização do estoque
    - 15 pontos por rota de motoboy
    - 15 pontos por dia de sedex
    """
    TIPO_APLICACAO = [
        ('automatica', 'Automática'),
        ('manual_gerente', 'Manual pelo Gerente'),
    ]
    
    nome_regra = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    ativa = models.BooleanField(default=True)
    tipo_aplicacao = models.CharField(max_length=20, choices=TIPO_APLICACAO)
    condicao_aplicacao = models.TextField(blank=True, help_text="Condição para aplicação automática")
    etapa_relacionada = models.ForeignKey(Etapa, on_delete=models.SET_NULL, null=True, blank=True, related_name='pontuacoes_fixas')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Pontuação Fixa Mensal'
        verbose_name_plural = 'Pontuações Fixas Mensais'
    
    def __str__(self):
        return f"{self.nome_regra} - {self.valor} pts ({self.get_tipo_aplicacao_display()})"


class BonusFaixa(models.Model):
    """
    Faixas de bônus por produtividade:
    - até 400 pontos: R$ 0
    - 401 a 600 pontos: R$ 150
    - 601 a 800 pontos: R$ 250
    - acima de 800: R$ 350 (teto)
    """
    faixa_min = models.DecimalField(max_digits=10, decimal_places=2)
    faixa_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # null = sem limite superior
    valor_em_reais = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['faixa_min']
        verbose_name = 'Faixa de Bônus'
        verbose_name_plural = 'Faixas de Bônus'
    
    def __str__(self):
        if self.faixa_max is None:
            return f"Acima de {self.faixa_min} pts = R$ {self.valor_em_reais}"
        return f"{self.faixa_min} - {self.faixa_max} pts = R$ {self.valor_em_reais}"
    
    @classmethod
    def calcular_bonus(cls, pontos_totais):
        """Calcula o bônus baseado na quantidade de pontos"""
        faixa = cls.objects.filter(
            ativo=True,
            faixa_min__lte=pontos_totais
        ).exclude(faixa_max__lt=pontos_totais).first()
        
        if faixa:
            return faixa.valor_em_reais
        return Decimal('0')


class HistoricoBonusMensal(models.Model):
    STATUS_PAGAMENTO = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('cancelado', 'Cancelado'),
    ]
    
    mes_referencia = models.DateField()
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bonus_mensais')
    pontos_totais_mes = models.DecimalField(max_digits=10, decimal_places=2)
    valor_em_reais_calculado = models.DecimalField(max_digits=10, decimal_places=2)
    status_pagamento = models.CharField(max_length=20, choices=STATUS_PAGAMENTO, default='pendente')
    timestamp_calculo = models.DateTimeField(auto_now_add=True)
    pago_em = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-mes_referencia', '-pontos_totais_mes']
        unique_together = ['mes_referencia', 'funcionario']
        verbose_name = 'Histórico de Bônus Mensal'
        verbose_name_plural = 'Histórico de Bônus Mensais'
    
    def __str__(self):
        return f"{self.funcionario.username} - {self.mes_referencia} - R$ {self.valor_em_reais_calculado}"


class ConfiguracaoExpedicao(models.Model):
    TIPO_EXPEDICAO = [
        ('motoboy', 'Motoboy'),
        ('sedex', 'Sedex'),
    ]
    
    TIPO_PONTUACAO_SEDEX = [
        ('por_envio', 'Por Envio'),
        ('por_dia', 'Por Dia'),
    ]
    
    tipo_expedicao = models.CharField(max_length=20, choices=TIPO_EXPEDICAO, unique=True)
    pontos_por_rota_motoboy = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pontos_fixos_diarios_motoboy = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tipo_pontuacao_sedex = models.CharField(max_length=20, choices=TIPO_PONTUACAO_SEDEX, default='por_envio')
    pontos_sedex = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuração de Expedição'
        verbose_name_plural = 'Configurações de Expedição'
    
    def __str__(self):
        return f"{self.get_tipo_expedicao_display()}"


class RegistroExpedicao(models.Model):
    ROTA_CHOICES = [
        ('motoboy', 'Motoboy'),
        ('sedex', 'Sedex'),
    ]
    
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE)
    configuracao = models.ForeignKey(ConfiguracaoExpedicao, on_delete=models.CASCADE, null=True, blank=True)
    
    # Novos campos para PedidoMestre (novo fluxo)
    pedidos_mestre = models.ManyToManyField('PedidoMestre', blank=True, related_name='registros_expedicao')
    rota_tipo = models.CharField(max_length=20, choices=ROTA_CHOICES, blank=True)
    total_pedidos = models.IntegerField(default=0)
    total_formulas = models.IntegerField(default=0)
    
    data = models.DateTimeField(auto_now_add=True)
    pontos_gerados = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacoes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-data']
        verbose_name = 'Registro de Expedição'
        verbose_name_plural = 'Registros de Expedição'
    
    def __str__(self):
        if self.pedidos_mestre.exists():
            return f"Expedição {self.rota_tipo.upper()} - {self.funcionario.username} - {self.data.strftime('%d/%m/%Y %H:%M')}"
        return f"{self.funcionario.username} - {self.configuracao.tipo_expedicao} - {self.data}"


class LogAuditoria(models.Model):
    ACAO_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('assumir_etapa', 'Assumir Etapa'),
        ('concluir_etapa', 'Concluir Etapa'),
        ('marcar_check', 'Marcar Checklist'),
        ('alterar_regra', 'Alterar Regra'),
        ('penalizacao', 'Penalização'),
        ('reverter_penalizacao', 'Reverter Penalização'),
        ('aprovar_pedido', 'Aprovar Pedido'),
        ('reprovar_pedido', 'Reprovar Pedido'),
        ('criar_etapa', 'Criar Etapa'),
        ('editar_etapa', 'Editar Etapa'),
        ('criar_usuario', 'Criar Usuário'),
        ('editar_usuario', 'Editar Usuário'),
        ('outros', 'Outros'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acao = models.CharField(max_length=50, choices=ACAO_CHOICES)
    descricao = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    dados_adicionais = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
    
    def __str__(self):
        usuario_nome = self.usuario.username if self.usuario else 'Sistema'
        return f"{usuario_nome} - {self.get_acao_display()} - {self.timestamp}"

class ConfiguracaoControleQualidade(models.Model):
    """
    Configuração geral do Controle de Qualidade
    Define a pontuação que cada formulário preenchido dará ao funcionário
    """
    nome_configuracao = models.CharField(max_length=200, default='Padrão', unique=True)
    pontos_por_formulario = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=5,
        help_text="Pontuação atribuída cada vez que um formulário de CQ é preenchido"
    )
    ativa = models.BooleanField(default=True)
    descricao = models.TextField(blank=True, help_text="Descrição da configuração")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuração de Controle de Qualidade'
        verbose_name_plural = 'Configurações de Controle de Qualidade'
    
    def __str__(self):
        return f"{self.nome_configuracao} - {self.pontos_por_formulario} pts"
    
    @classmethod
    def get_configuracao_ativa(cls):
        """Retorna a configuração ativa, ou cria uma padrão se não existir"""
        config = cls.objects.filter(ativa=True).first()
        if not config:
            config, _ = cls.objects.get_or_create(
                nome_configuracao='Padrão',
                defaults={'pontos_por_formulario': 5, 'ativa': True}
            )
        return config


class ControlePergunta(models.Model):
    """
    Define perguntas para o Controle de Qualidade
    Admin cria as perguntas e define o tipo de resposta esperada
    Perguntas NÃO possuem pontuação individual - pontuação vem da ConfiguracaoControleQualidade
    """
    TIPO_CAMPO_CHOICES = [
        ('texto', 'Texto Simples'),
        ('textarea', 'Texto Longo'),
        ('checkbox', 'Sim/Não'),
        ('selecao', 'Seleção Múltipla'),
        ('numero', 'Número'),
    ]
    
    pergunta = models.CharField(max_length=500, help_text="Ex: Conferiu os produtos?")
    tipo_campo = models.CharField(max_length=20, choices=TIPO_CAMPO_CHOICES, default='texto')
    descricao = models.TextField(blank=True, help_text="Descrição adicional ou instruções")
    ativo = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0, help_text="Ordem de apresentação das perguntas")
    obrigatorio = models.BooleanField(default=True, help_text="Se a resposta é obrigatória")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['ordem', 'id']
        verbose_name = 'Pergunta de Controle de Qualidade'
        verbose_name_plural = 'Perguntas de Controle de Qualidade'
    
    def __str__(self):
        return f"{self.pergunta}"


class ControlePerguntaOpcao(models.Model):
    """
    Opções para perguntas de seleção múltipla ou checkbox
    Ex: Para checkbox "Conferiu os produtos?" - opções seriam "Sim" e "Não"
    """
    pergunta = models.ForeignKey(ControlePergunta, on_delete=models.CASCADE, related_name='opcoes')
    texto_opcao = models.CharField(max_length=200)
    ordem = models.IntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['ordem', 'id']
        verbose_name = 'Opção de Pergunta'
        verbose_name_plural = 'Opções de Pergunta'
    
    def __str__(self):
        return f"{self.pergunta.pergunta} - {self.texto_opcao}"


class HistoricoControleQualidade(models.Model):
    """
    Formulário de Controle de Qualidade independente (não vinculado a pedidos)
    Funciona como um formulário que o funcionário preenche quando necessário
    """
    # Dados do Controle de Qualidade preenchidos pelo funcionário
    id_controle = models.CharField(max_length=100, null=True, blank=True, help_text="ID ou referência do item (preenchido pelo funcionário)")
    nome_item = models.CharField(max_length=200, null=True, blank=True, help_text="Nome do item/produto sendo inspecionado")
    codigo_item = models.CharField(max_length=100, blank=True, help_text="Código do item (opcional)")
    
    # Dados do sistema
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='formularios_controle_qualidade')
    pontuacao = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Pontuação obtida no formulário")
    
    preenchido_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-preenchido_em']
        verbose_name = 'Formulário de Controle de Qualidade'
        verbose_name_plural = 'Formulários de Controle de Qualidade'
    
    def __str__(self):
        return f"CQ: {self.id_controle} - {self.nome_item} - {self.funcionario.username}"


class RespostaControleQualidade(models.Model):
    """
    Armazena as respostas individuais para cada pergunta
    """
    historico_controle = models.ForeignKey(HistoricoControleQualidade, on_delete=models.CASCADE, related_name='respostas')
    pergunta = models.ForeignKey(ControlePergunta, on_delete=models.CASCADE)
    resposta_texto = models.TextField(blank=True, help_text="Para respostas de texto ou textarea")
    resposta_opcao = models.ForeignKey(ControlePerguntaOpcao, on_delete=models.SET_NULL, null=True, blank=True, help_text="Para respostas de checkbox ou seleção")
    preenchido_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['pergunta__ordem', 'pergunta__id']
        verbose_name = 'Resposta de Controle de Qualidade'
        verbose_name_plural = 'Respostas de Controle de Qualidade'
        unique_together = ['historico_controle', 'pergunta']
    
    def __str__(self):
        if self.resposta_opcao:
            return f"{self.pergunta.pergunta} - {self.resposta_opcao.texto_opcao}"
        return f"{self.pergunta.pergunta} - {self.resposta_texto[:50]}"


class ConfiguracaoAPI(models.Model):
    """
    Configuração de APIs externas
    Armazena URLs, autenticações e outras configurações de forma centralizada
    Permite gerenciar tudo pelo Django Admin ao invés de hardcodear no código
    """
    TIPO_AUTENTICACAO = [
        ('nenhuma', 'Nenhuma'),
        ('bearer_token', 'Bearer Token'),
        ('api_key', 'API Key'),
        ('login_senha', 'Usuário e Senha'),
        ('custom', 'Customizada'),
    ]
    
    nome = models.CharField(
        max_length=200, 
        unique=True,
        help_text="Nome descritivo da API (ex: API Pedidos, API Estoque)"
    )
    url_base = models.URLField(
        help_text="URL base da API (ex: https://api.exemplo.com/tabelas/FC0M100)"
    )
    descricao = models.TextField(
        blank=True,
        help_text="Descrição sobre a API e seu propósito"
    )
    
    # Autenticação
    tipo_autenticacao = models.CharField(
        max_length=20,
        choices=TIPO_AUTENTICACAO,
        default='nenhuma',
        help_text="Tipo de autenticação requerida pela API"
    )
    bearer_token = models.CharField(
        max_length=500,
        blank=True,
        help_text="Token para autenticação Bearer (se aplicável)"
    )
    api_key = models.CharField(
        max_length=500,
        blank=True,
        help_text="API Key para autenticação (se aplicável)"
    )
    usuario = models.CharField(
        max_length=200,
        blank=True,
        help_text="Usuário para autenticação (se aplicável)"
    )
    senha = models.CharField(
        max_length=200,
        blank=True,
        help_text="Senha para autenticação (se aplicável)"
    )
    headers_customizados = models.JSONField(
        null=True,
        blank=True,
        help_text="Headers customizados em formato JSON (ex: {\"Custom-Header\": \"value\"})"
    )
    
    # Configurações
    timeout = models.IntegerField(
        default=30,
        help_text="Timeout em segundos para requisições"
    )
    ativa = models.BooleanField(
        default=True,
        help_text="Se a API está ativa para sincronização"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuração de API'
        verbose_name_plural = 'Configurações de API'
    
    def __str__(self):
        return f"{self.nome} - {self.url_base[:50]}"
    
    def obter_headers_requisicao(self):
        """Retorna os headers para a requisição HTTP"""
        headers = {}
        
        if self.tipo_autenticacao == 'bearer_token' and self.bearer_token:
            headers['Authorization'] = f'Bearer {self.bearer_token}'
        elif self.tipo_autenticacao == 'api_key' and self.api_key:
            headers['X-API-Key'] = self.api_key
        elif self.tipo_autenticacao == 'custom' and self.headers_customizados:
            headers.update(self.headers_customizados)
        
        return headers


class AgendamentoSincronizacao(models.Model):
    """
    Define quando e com que frequência a API deve ser sincronizada
    Permite agendamentos complexos: dias específicos, horários múltiplos, etc
    """
    DIAS_SEMANA = [
        ('segunda', 'Segunda-feira'),
        ('terca', 'Terça-feira'),
        ('quarta', 'Quarta-feira'),
        ('quinta', 'Quinta-feira'),
        ('sexta', 'Sexta-feira'),
        ('sabado', 'Sábado'),
        ('domingo', 'Domingo'),
    ]
    
    api = models.ForeignKey(
        ConfiguracaoAPI,
        on_delete=models.CASCADE,
        related_name='agendamentos',
        help_text="API a ser sincronizada"
    )
    nome = models.CharField(
        max_length=200,
        help_text="Nome descritivo do agendamento (ex: Sincronização Matinal)"
    )
    
    # Dias da semana
    executar_todos_os_dias = models.BooleanField(
        default=True,
        help_text="Se deve executar todos os dias"
    )
    dias_semana = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de dias se não for todos os dias (ex: ['segunda', 'quarta', 'sexta'])"
    )
    
    # Horários
    horario_execucao = models.TimeField(
        help_text="Horário em que a sincronização será executada (ex: 06:00)"
    )
    
    # Paginações (configuração de quantas páginas buscar)
    paginacoes = models.JSONField(
        default=list,
        help_text="Lista de dicts com paginações (ex: [{\"pagina\": 1, \"tamanho\": 50}, {\"pagina\": 2, \"tamanho\": 50}])"
    )
    
    # Status
    ativo = models.BooleanField(
        default=True,
        help_text="Se o agendamento está ativo"
    )
    descricao = models.TextField(
        blank=True,
        help_text="Notas adicionais sobre este agendamento"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['api', 'horario_execucao']
        verbose_name = 'Agendamento de Sincronização'
        verbose_name_plural = 'Agendamentos de Sincronização'
    
    def __str__(self):
        dias_texto = "Todos os dias" if self.executar_todos_os_dias else ", ".join(self.dias_semana)
        return f"{self.api.nome} - {self.horario_execucao} ({dias_texto})"
    
    def clean(self):
        if not self.executar_todos_os_dias and not self.dias_semana:
            raise ValidationError("Se não executar todos os dias, selecione pelo menos um dia da semana")


# ========== NOVOS MODELOS PARA FLUXO COM MÚLTIPLAS FÓRMULAS ==========

class PedidoMestre(models.Model):
    """
    Agrupa todas as fórmulas de um pedido pelo NRORC (identificador único)
    Exemplo: NRORC 73020 pode ter 2 fórmulas (Vitamina A e Ferro)
    """
    STATUS_CHOICES = [
        ('em_processamento', 'Em Processamento'),
        ('pronto_para_expedicao', 'Pronto para Expedição'),
        ('em_rota_motoboy', 'Em Rota Motoboy'),
        ('em_rota_sedex', 'Em Rota Sedex'),
        ('expedido', 'Expedido'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]
    
    nrorc = models.BigIntegerField(unique=True, db_index=True, help_text="Número RC do pedido (identificador único da API)")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='em_processamento')
    cliente = models.CharField(max_length=200, blank=True, help_text="Nome do cliente")
    observacoes = models.TextField(blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
    
    def __str__(self):
        return f"NRORC {self.nrorc} - {self.status}"
    
    @property
    def total_formulas(self):
        """Retorna total de fórmulas neste pedido"""
        return self.formulas.count()
    
    @property
    def formulas_prontas(self):
        """Retorna quantidade de fórmulas prontas para expedição"""
        return self.formulas.filter(status='pronto_para_expedicao').count()
    
    @property
    def pode_ir_para_rota(self):
        """Verifica se o pedido pode ser enviado para rota (todas as fórmulas prontas)"""
        return self.total_formulas > 0 and self.total_formulas == self.formulas_prontas
    
    @property
    def motivo_nao_pode_ir_rota(self):
        """Retorna motivo se o pedido não pode ir para rota"""
        if self.total_formulas == 0:
            return "Sem fórmulas"
        
        pendentes = self.total_formulas - self.formulas_prontas
        # Buscar status das que não estão prontas
        formulas_nao_prontas = self.formulas.exclude(status='pronto_para_expedicao').values('status').distinct()
        status_list = ', '.join([f.get('status') for f in formulas_nao_prontas])
        
        return f"Aguardando conclusão de {pendentes} fórmula(s) em: {status_list}"
    
    def validar_e_atualizar_status(self):
        """Valida se todas as fórmulas estão prontas e atualiza status do PedidoMestre"""
        total = self.total_formulas
        prontas = self.formulas_prontas
        
        if total == 0:
            return  # Nenhuma fórmula ainda
        
        if prontas == total:
            # Todas prontas!
            self.status = 'pronto_para_expedicao'
        else:
            # Parcialmente
            self.status = 'em_processamento'
        
        self.save()


class FormulaItem(models.Model):
    """
    Representa uma fórmula específica dentro de um pedido
    Exemplo: VITAMINA A + D3 + TCM (10ML) é uma FormulaItem do NRORC 73020
    Cada fórmula segue o fluxo completo: Triagem → Produção → Qualidade → Expedição
    """
    STATUS_CHOICES = [
        ('em_triagem', 'Em Triagem'),
        ('em_producao', 'Em Produção'),
        ('em_qualidade', 'Em Qualidade'),
        ('pronto_para_expedicao', 'Pronto para Expedição'),
        ('expedido', 'Expedido'),
        ('cancelado', 'Cancelado'),
    ]
    
    pedido_mestre = models.ForeignKey(PedidoMestre, on_delete=models.CASCADE, related_name='formulas')
    
    # Dados da fórmula
    descricao = models.TextField(help_text="Descrição da fórmula (ex: VITAMINA A + D3 + TCM | 10ML)")
    quantidade = models.IntegerField(default=1, help_text="Quantidade de unidades")
    volume_ml = models.CharField(max_length=20, blank=True, help_text="Volume em ML se aplicável (ex: 10ML, 60ML)")
    
    # Dados da API
    id_api = models.CharField(max_length=100, unique=True, db_index=True, help_text="ID único da fórmula vindo da API")
    serieo = models.CharField(max_length=20, blank=True, help_text="Série do item (SERIEO)")
    price_unit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Preço unitário")
    price_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Preço total")
    
    # Status do fluxo
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='em_triagem')
    etapa_atual = models.ForeignKey(Etapa, on_delete=models.SET_NULL, null=True, blank=True)
    funcionario_na_etapa = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='formulas_assumidas')
    
    # Status de tarefa (ativo/pendente) - limite de 5 tarefas, apenas 1 ativa
    STATUS_TAREFA_CHOICES = [
        ('disponivel', 'Disponível'),
        ('ativo', 'Ativo'),
        ('pendente', 'Pendente'),
        ('concluido', 'Concluído'),
    ]
    eh_tarefa_ativa = models.BooleanField(default=False, help_text="Indica se é a tarefa ativa do funcionário nesta etapa")
    
    # Rastreamento
    data_criacao_api = models.DateField(null=True, blank=True, help_text="Data de criação no sistema da API")
    data_atualizacao_api = models.DateField(null=True, blank=True, help_text="Data de atualização no sistema da API")
    datetime_atualizacao_api = models.DateTimeField(null=True, blank=True, db_index=True, help_text="Data + Hora de atualização na API (DTALT + HRALT)")
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['pedido_mestre', 'criado_em']
        verbose_name = 'Item de Fórmula'
        verbose_name_plural = 'Itens de Fórmula'
    
    def __str__(self):
        return f"{self.pedido_mestre.nrorc} - {self.descricao[:50]}"
    
    def get_tipo_forma(self):
        """Extrai o tipo de forma (cápsula, líquido, etc.) da descrição"""
        if not self.descricao:
            return "Desconhecido"
        
        desc_upper = self.descricao.upper()
        
        if "CAPSULA" in desc_upper or "CAP" in desc_upper:
            return "Cápsula"
        elif "SACHE" in desc_upper or "SACHÊ" in desc_upper or "ENVELOPE" in desc_upper:
            return "Sachê"
        elif "ML" in desc_upper or "LIQUIDO" in desc_upper or "LÍQUIDO" in desc_upper or "XAROPE" in desc_upper or "TCM LIQUIDO" in desc_upper:
            return "Líquido"
        elif "CREME" in desc_upper or "POMADA" in desc_upper or "GEL" in desc_upper:
            return "Creme"
        elif "LOÇÃO" in desc_upper or "LOCION" in desc_upper:
            return "Loção"
        elif "SHAMPOO" in desc_upper:
            return "Shampoo"
        elif "SHOT" in desc_upper:
            return "Shot"
        elif "ÓVULO" in desc_upper or "OVULO" in desc_upper:
            return "Óvulo"
        elif "SUBLINGUAL" in desc_upper or "PASTILHA" in desc_upper:
            return "Comprimido"
        elif "OLEOSA" in desc_upper or "OLEOSO" in desc_upper:
            return "Oleosa"
        elif "GOMA" in desc_upper or "GUMMY" in desc_upper:
            return "Goma"
        elif "CHOCOLATE" in desc_upper:
            return "Chocolate"
        elif "FILME" in desc_upper:
            return "Filme"
        else:
            return "Outro"
    
    def get_volume_display(self):
        """Retorna o volume/quantidade formatado dependendo do tipo de forma"""
        import re
        
        if not self.descricao:
            return self.volume_ml or "-"
        
        desc_upper = self.descricao.upper()
        
        # Para cápsulas, buscar padrão NNNCAP (ex: 30CAP)
        if "CAPSULA" in desc_upper or "CAP" in desc_upper:
            # Procura por padrão como "30CAP", "60CAP", etc.
            match = re.search(r'(\d+)\s*CAP(?:SULA)?', desc_upper)
            if match:
                return f"{match.group(1)} cápsulas"
            # Se tiver quantidade de unidades, retorna
            if self.quantidade:
                return f"{self.quantidade} unidades"
            return "-"
        
        # Para sachês, retorna quantidade
        elif "SACHE" in desc_upper or "SACHÊ" in desc_upper or "ENVELOPE" in desc_upper:
            if self.quantidade:
                return f"{self.quantidade} sachês"
            return "-"
        
        # Para outros, retorna volume_ml
        else:
            return self.volume_ml or "-"
    
    def avancar_etapa(self):
        """Avança a fórmula para a próxima etapa"""
        if self.etapa_atual:
            proxima = self.etapa_atual.proxima_etapa()
            if proxima:
                self.etapa_atual = proxima
                # Atualizar status
                if proxima.nome.lower() == 'triagem':
                    self.status = 'em_triagem'
                elif proxima.nome.lower() == 'produção':
                    self.status = 'em_producao'
                elif proxima.nome.lower() == 'qualidade':
                    self.status = 'em_qualidade'
                elif proxima.nome.lower() == 'expedição':
                    self.status = 'pronto_para_expedicao'
                    # Validar pedido mestre
                    self.pedido_mestre.validar_e_atualizar_status()
                
                self.funcionario_na_etapa = None
                self.save()
            else:
                # Não há próxima etapa - fórmula expedida
                self.status = 'expedido'
                self.etapa_atual = None
                self.funcionario_na_etapa = None
                self.concluido_em = timezone.now()
                self.save()
                # Validar pedido mestre
                self.pedido_mestre.validar_e_atualizar_status()


class HistoricoEtapaFormula(models.Model):
    """
    Rastreia cada passagem de uma fórmula por uma etapa
    Similar ao HistoricoEtapa, mas versionado para FormulaItem
    """
    formula = models.ForeignKey(FormulaItem, on_delete=models.CASCADE, related_name='historico_etapas')
    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE)
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    timestamp_inicio = models.DateTimeField(auto_now_add=True)
    timestamp_fim = models.DateTimeField(null=True, blank=True)
    
    # Pontuação
    pontos_gerados = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Pontos ganhos nesta etapa")
    
    # Expedição
    rota_tipo = models.CharField(
        max_length=20,
        choices=[('motoboy', 'Motoboy'), ('sedex', 'Sedex')],
        null=True, blank=True,
        help_text="Tipo de rota (apenas preenchido na Expedição)"
    )
    
    observacoes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp_inicio']
        verbose_name = 'Histórico de Etapa da Fórmula'
        verbose_name_plural = 'Históricos de Etapas das Fórmulas'
    
    def __str__(self):
        return f"{self.formula.pedido_mestre.nrorc} - {self.etapa.nome} - {self.funcionario.username}"
    
    @property
    def tempo_gasto_minutos(self):
        """Calcula tempo gasto em minutos"""
        if self.timestamp_fim and self.timestamp_inicio:
            delta = self.timestamp_fim - self.timestamp_inicio
            return int(delta.total_seconds() // 60)
        return None
    
    @property
    def tempo_gasto_formatado(self):
        """Retorna tempo gasto formatado"""
        if self.timestamp_fim and self.timestamp_inicio:
            delta = self.timestamp_fim - self.timestamp_inicio
            total_segundos = int(delta.total_seconds())
            
            horas = total_segundos // 3600
            minutos = (total_segundos % 3600) // 60
            segundos = total_segundos % 60
            
            partes = []
            if horas > 0:
                partes.append(f"{horas}h")
            if minutos > 0:
                partes.append(f"{minutos}min")
            if segundos > 0 or not partes:
                partes.append(f"{segundos}seg")
            
            return " ".join(partes)
        return "-"


class ChecklistExecucaoFormula(models.Model):
    """
    Rastreia execução de checklists para fórmulas (novo fluxo)
    Similar ao ChecklistExecucao, mas vinculado a HistoricoEtapaFormula
    """
    historico_etapa = models.ForeignKey(HistoricoEtapaFormula, on_delete=models.CASCADE, related_name='checklists_executados')
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE)
    marcado = models.BooleanField(default=False)
    pontos_gerados = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    marcado_em = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Execução de Checklist de Fórmula'
        verbose_name_plural = 'Execuções de Checklists de Fórmulas'
        unique_together = ('historico_etapa', 'checklist')
    
    def __str__(self):
        return f"{self.checklist.nome} - {'OK' if self.marcado else 'PENDENTE'}"