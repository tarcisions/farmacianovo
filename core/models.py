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


class RegraProducao(models.Model):
    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, related_name='regras_producao')
    faixa_min = models.IntegerField()
    faixa_max = models.IntegerField()
    pontos_por_unidade = models.DecimalField(max_digits=10, decimal_places=4)
    pontos_fixos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ativo = models.BooleanField(default=True)
    versao = models.CharField(max_length=20, default='1.0')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['faixa_min']
        verbose_name = 'Regra de Produção'
        verbose_name_plural = 'Regras de Produção'
    
    def __str__(self):
        return f"{self.etapa.nome}: {self.faixa_min}-{self.faixa_max} (v{self.versao})"
    
    @classmethod
    def get_versao_ativa(cls, etapa):
        return cls.objects.filter(etapa=etapa, ativo=True).order_by('-versao')
    
    @classmethod
    def calcular_pontos(cls, etapa, quantidade):
        regra = cls.objects.filter(
            etapa=etapa,
            ativo=True,
            faixa_min__lte=quantidade,
            faixa_max__gte=quantidade
        ).order_by('-versao').first()
        
        if regra:
            return (Decimal(str(quantidade)) * regra.pontos_por_unidade) + regra.pontos_fixos
        return Decimal('0')


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


class Pedido(models.Model):
    STATUS_CHOICES = [
        ('em_fluxo', 'Em Fluxo'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]
    
    STATUS_FILA = [
        ('ativo', 'Ativo'),
        ('pendente', 'Pendente'),
    ]
    
    # Campos da API
    tipo = models.ForeignKey(TipoProduto, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos')
    nome = models.CharField(max_length=200)  # Nome da fórmula/produto
    quantidade = models.IntegerField()
    codigo_pedido = models.CharField(max_length=50, unique=False, blank=True)  # Código gerado para referência (não único)
    
    # Campos da API externa - IDs separados em colunas
    id_api = models.BigIntegerField(unique=True, db_index=True, null=True, blank=True)  # ID - ID único do item
    id_pedido_api = models.BigIntegerField(null=True, blank=True, db_index=True)  # IDPEDIDO
    id_pedido_web = models.BigIntegerField(null=True, blank=True, db_index=True)  # IDPEDIDOWEB
    descricao_web = models.TextField(blank=True)  # DESCRICAOWEB
    price_unit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # PRUNI
    price_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # VRTOT
    data_atualizacao_api = models.DateField(null=True, blank=True)  # DTALT
    hora_atualizacao_api = models.TimeField(null=True, blank=True)  # HRALT
    tipo_identificado = models.CharField(
        max_length=50,
        default='desconhecido',
        help_text='Tipo identificado automaticamente da descrição (desconhecido = requer ajuste manual)'
    )  # Rastreamento de tipo identificado
    
    # Campos do sistema
    etapa_atual = models.ForeignKey(Etapa, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_na_etapa')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='em_fluxo')
    funcionario_na_etapa = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_assumidos')
    status_fila = models.CharField(max_length=20, choices=STATUS_FILA, default='ativo', help_text='Status na fila de trabalho (Ativo/Pendente)')
    tipo_expedicao = models.CharField(
        max_length=20,
        choices=[('motoboy', 'Motoboy'), ('sedex', 'Sedex')],
        null=True,
        blank=True,
        help_text='Tipo de expedição selecionado pelo funcionário'
    )
    
    informacoes_gerais = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-data_atualizacao_api', '-hora_atualizacao_api']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
    
    def __str__(self):
        return f"Pedido #{self.codigo_pedido} - {self.nome}"
    
    def pode_assumir(self, etapa):
        if self.etapa_atual != etapa:
            return False, "Esta não é a etapa atual do pedido"
        if self.funcionario_na_etapa is not None:
            return False, "Pedido já assumido por outro funcionário"
        
        if etapa.sequencia > 1:
            etapa_anterior = Etapa.objects.filter(sequencia=etapa.sequencia - 1).first()
            if etapa_anterior:
                historico = HistoricoEtapa.objects.filter(
                    pedido=self,
                    etapa=etapa_anterior,
                    timestamp_fim__isnull=False
                ).exists()
                if not historico:
                    return False, "Etapa anterior não foi concluída"
        
        return True, "OK"
    
    def avancar_etapa(self):
        if self.etapa_atual:
            proxima = self.etapa_atual.proxima_etapa()
            if proxima:
                self.etapa_atual = proxima
                self.funcionario_na_etapa = None
                self.save()
            else:
                self.status = 'concluido'
                self.concluido_em = timezone.now()
                self.etapa_atual = None
                self.funcionario_na_etapa = None
                self.save()
    
    def pode_assumir_fila(self, usuario):
        """Verifica se o usuário pode assumir este pedido"""
        # Verificar se é etapa de Expedição
        is_expedicao = self.etapa_atual and self.etapa_atual.nome.lower() == 'expedição'
        
        if not is_expedicao:
            # Máximo 5 pedidos por funcionário (APENAS para etapas diferentes de Expedição)
            pedidos_count = Pedido.objects.filter(
                funcionario_na_etapa=usuario,
                status='em_fluxo'
            ).count()
            
            if pedidos_count >= 5:
                return False, "Você atingiu o máximo de 5 pedidos simultâneos"
            
            # Verificar se há mais de 1 ativo por funcionário (apenas para outras etapas)
            ativo_count = Pedido.objects.filter(
                funcionario_na_etapa=usuario,
                status='em_fluxo',
                status_fila='ativo'
            ).count()
            
            if ativo_count >= 1 and self.status_fila == 'ativo':
                return False, "Você já tem 1 pedido ativo. Coloque-o como pendente para ativar este."
        
        return True, "OK"
    
    def marcar_como_pendente(self, em_sessao_expedicao=False):
        """Marca o pedido como pendente (não aplicável se tipo_expedicao for motoboy ou sedex)"""
        # Se tipo_expedicao é motoboy ou sedex, não pode ficar pendente
        if self.tipo_expedicao in ['motoboy', 'sedex']:
            return False, "Pedidos com expedição definida (Motoboy/Sedex) não podem ficar pendentes"
        
        # Se está em sessão de expedição (tela de motoboy/sedex), não pode ficar pendente
        if em_sessao_expedicao:
            return False, "Pedidos em sessão de expedição não podem ficar pendentes"
        
        self.status_fila = 'pendente'
        self.save()
        return True, "Pedido marcado como pendente"
    
    def marcar_como_ativo(self):
        """Marca o pedido como ativo e coloca outros em pendente (NÃO aplicável para Expedição)"""
        if not self.funcionario_na_etapa:
            return False, "Pedido não tem funcionário designado"
        
        # Para Expedição, sempre é ativo (sem lógica de pendente)
        is_expedicao = self.etapa_atual and self.etapa_atual.nome.lower() == 'expedição'
        if is_expedicao:
            self.status_fila = 'ativo'
            self.save()
            return True, "Pedido está ativo (Expedição não possui status pendente)"
        
        # Para outras etapas: colocar todos os outros pedidos deste funcionário como pendente
        Pedido.objects.filter(
            funcionario_na_etapa=self.funcionario_na_etapa,
            status='em_fluxo',
            status_fila='ativo'
        ).exclude(id=self.id).update(status_fila='pendente')
        
        # Ativar este pedido
        self.status_fila = 'ativo'
        self.save()
        return True, "Pedido ativado com sucesso"


class HistoricoEtapa(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='historico_etapas')
    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE)
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp_inicio = models.DateTimeField(auto_now_add=True)
    timestamp_fim = models.DateTimeField(null=True, blank=True)
    versao_configuracao_pontuacao = models.ForeignKey(ConfiguracaoPontuacao, on_delete=models.SET_NULL, null=True, blank=True)
    quantidade_produzida = models.IntegerField(default=0)
    pontos_gerados = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacoes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp_inicio']
        verbose_name = 'Histórico de Etapa'
        verbose_name_plural = 'Histórico de Etapas'
    
    def __str__(self):
        return f"{self.pedido} - {self.etapa.nome} - {self.funcionario.username}"
    
    @property
    def tempo_gasto_minutos(self):
        """Calcula o tempo gasto em minutos"""
        if self.timestamp_fim and self.timestamp_inicio:
            delta = self.timestamp_fim - self.timestamp_inicio
            return int(delta.total_seconds() // 60)
        return None
    
    @property
    def tempo_gasto_formatado(self):
        """Retorna tempo gasto formatado como 'Xh Xmin Xseg' ou apenas os campos relevantes"""
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
            if segundos > 0 or not partes:  # Mostra segundos sempre que houver, ou se for 0 segundos (menos de 1 minuto)
                partes.append(f"{segundos}seg")
            
            return " ".join(partes)
        return "-"


class ChecklistExecucao(models.Model):
    historico_etapa = models.ForeignKey(HistoricoEtapa, on_delete=models.CASCADE, related_name='checklists_executados')
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE)
    marcado = models.BooleanField(default=False)
    pontos_gerados = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    marcado_em = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Execução de Checklist'
        verbose_name_plural = 'Execuções de Checklists'
    
    def __str__(self):
        return f"{self.checklist.nome} - {'✓' if self.marcado else '✗'}"


class PontuacaoFuncionario(models.Model):
    ORIGEM_CHOICES = [
        ('etapa', 'Etapa'),
        ('producao', 'Produção'),
        ('check', 'Checklist'),
        ('penalizacao', 'Penalização'),
        ('expedicao', 'Expedição'),
        ('mensal', 'Bonificação Mensal'),
    ]
    
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pontuacoes')
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=True, blank=True)
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


class HistoricoAplicacaoPontuacaoFixa(models.Model):
    regra = models.ForeignKey(PontuacaoFixaMensal, on_delete=models.CASCADE, related_name='historico_aplicacoes')
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pontuacoes_fixas_recebidas')
    mes_referencia = models.DateField()
    pontos_aplicados = models.DecimalField(max_digits=10, decimal_places=2)
    aplicado_em = models.DateTimeField(auto_now_add=True)
    aplicado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pontuacoes_fixas_aplicadas')
    justificativa = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-aplicado_em']
        verbose_name = 'Histórico de Aplicação de Pontuação Fixa'
        verbose_name_plural = 'Histórico de Aplicações de Pontuação Fixa'
    
    def __str__(self):
        return f"{self.regra.nome_regra} - {self.funcionario.username} - {self.mes_referencia}"


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
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expedicoes')
    configuracao = models.ForeignKey(ConfiguracaoExpedicao, on_delete=models.CASCADE)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=True, blank=True)
    data = models.DateTimeField(auto_now_add=True)
    pontos_gerados = models.DecimalField(max_digits=10, decimal_places=2)
    observacoes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-data']
        verbose_name = 'Registro de Expedição'
        verbose_name_plural = 'Registros de Expedição'
    
    def __str__(self):
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

class ControlePergunta(models.Model):
    """
    Define perguntas para o Controle de Qualidade
    Admin cria as perguntas e define o tipo de resposta esperada
    """
    TIPO_CAMPO_CHOICES = [
        ('texto', 'Texto Simples'),
        ('textarea', 'Texto Longo'),
        ('checkbox', 'Sim/Não'),
        ('selecao', 'Seleção Múltipla'),
        ('numero', 'Número'),
    ]
    
    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, related_name='perguntas_controle_qualidade')
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
        unique_together = ['etapa', 'pergunta']
    
    def __str__(self):
        return f"{self.etapa.nome} - {self.pergunta}"


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
    Histórico das respostas do Controle de Qualidade preenchido pelo funcionário
    """
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='historico_controle_qualidade')
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='respostas_controle_qualidade')
    historico_etapa = models.OneToOneField(HistoricoEtapa, on_delete=models.CASCADE, related_name='controle_qualidade', null=True, blank=True)
    preenchido_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-preenchido_em']
        verbose_name = 'Histórico de Controle de Qualidade'
        verbose_name_plural = 'Histórico de Controles de Qualidade'
    
    def __str__(self):
        return f"{self.pedido} - {self.funcionario.username} - {self.preenchido_em.strftime('%d/%m/%Y %H:%M')}"


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