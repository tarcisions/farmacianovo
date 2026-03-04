"""
Funcoes auxiliares para calculo de pontuacao e bonus
Sem jobs, sem schedules - tudo calculado on-demand
"""

from django.contrib.auth.models import User
from django.db.models import Sum
from datetime import date
from decimal import Decimal

from core.models import PontuacaoFuncionario, Penalizacao, BonusFaixa


def calcular_pontos_mes(funcionario, mes_referencia=None):
    """
    Calcula os pontos LIQUIDOS de um funcionário em um mês
    Pontos = sum(PontuacaoFuncionario) - sum(Penalizacao)
    
    Args:
        funcionario: User object
        mes_referencia: date com dia 1 do mês (ex: 2026-03-01)
                       Se None, usa mês atual
    
    Returns:
        Decimal com pontos líquidos
    """
    if mes_referencia is None:
        hoje = date.today()
        mes_referencia = hoje.replace(day=1)
    
    # Somar pontuações do mês
    pontos_ganhos = PontuacaoFuncionario.objects.filter(
        funcionario=funcionario,
        mes_referencia=mes_referencia
    ).aggregate(total=Sum('pontos'))['total'] or Decimal('0')
    
    # Subtrair penalizações do mês (não revertidas)
    pontos_perdidos = Penalizacao.objects.filter(
        funcionario=funcionario,
        timestamp__year=mes_referencia.year,
        timestamp__month=mes_referencia.month,
        revertida=False
    ).aggregate(total=Sum('pontos'))['total'] or Decimal('0')
    
    # Pontos líquidos
    pontos_liquidos = pontos_ganhos - pontos_perdidos
    
    return max(pontos_liquidos, Decimal('0'))  # Não pode ser negativo


def calcular_bonus_mes(funcionario, mes_referencia=None):
    """
    Calcula o bônus em R$ baseado no pontos líquidos do mês
    
    Returns:
        Decimal com valor em reais
    """
    pontos = calcular_pontos_mes(funcionario, mes_referencia)
    bonus = BonusFaixa.calcular_bonus(pontos)
    
    return bonus


def get_resumo_mes(funcionario, mes_referencia=None):
    """
    Retorna dict com resumo completo do mês
    """
    if mes_referencia is None:
        hoje = date.today()
        mes_referencia = hoje.replace(day=1)
    
    pontos_ganhos = PontuacaoFuncionario.objects.filter(
        funcionario=funcionario,
        mes_referencia=mes_referencia
    ).aggregate(total=Sum('pontos'))['total'] or Decimal('0')
    
    penalizacoes = Penalizacao.objects.filter(
        funcionario=funcionario,
        timestamp__year=mes_referencia.year,
        timestamp__month=mes_referencia.month,
        revertida=False
    )
    
    pontos_perdidos = penalizacoes.aggregate(total=Sum('pontos'))['total'] or Decimal('0')
    
    pontos_liquidos = max(pontos_ganhos - pontos_perdidos, Decimal('0'))
    bonus = BonusFaixa.calcular_bonus(pontos_liquidos)
    
    return {
        'mes': mes_referencia,
        'funcionario': funcionario,
        'pontos_ganhos': pontos_ganhos,
        'penalizacoes': penalizacoes,
        'pontos_perdidos': pontos_perdidos,
        'pontos_liquidos': pontos_liquidos,
        'bonus_reais': bonus,
    }
