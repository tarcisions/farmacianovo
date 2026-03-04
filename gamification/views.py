from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from core.models import BonusFaixa, PontuacaoFuncionario, HistoricoBonusMensal
from core.utils_pontuacao import get_resumo_mes
from django.utils import timezone
from django.db.models import Sum, Q, Count
from django.core.paginator import Paginator
from datetime import date, timedelta
from decimal import Decimal

# Dicionário de meses em português
MESES_PT = {
    1: 'Janeiro',
    2: 'Fevereiro', 
    3: 'Março',
    4: 'Abril',
    5: 'Maio',
    6: 'Junho',
    7: 'Julho',
    8: 'Agosto',
    9: 'Setembro',
    10: 'Outubro',
    11: 'Novembro',
    12: 'Dezembro'
}

def formatar_mes_pt(data):
    """Formata data como 'Mês/Ano' em português"""
    return f"{MESES_PT[data.month]}/{data.year}"

@login_required
def pontuacao_view(request):
    """
    Lista de funcionários com seus pontos e bônus do mês (tabela com filtros e paginação)
    Apenas para gerentes/admins
    """
    if not (request.user.groups.filter(name__in=['Superadmin', 'Gerente']).exists() or request.user.is_superuser):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')

    # Filtros
    mes_param = request.GET.get('mes', '')
    busca = request.GET.get('busca', '').strip()
    ordenar = request.GET.get('ordenar', '-pontos')  # -pontos, nome, bonus
    page_number = request.GET.get('page', 1)

    hoje = date.today()
    
    # Parse mês (pode ser YYYY-MM ou vazio)
    if mes_param:
        try:
            # Se vier como YYYY-MM, converte para data
            partes = mes_param.split('-')
            if len(partes) == 2:
                ano, mes = int(partes[0]), int(partes[1])
                mes_selecionado = date(ano, mes, 1)
            else:
                mes_selecionado = hoje.replace(day=1)
        except:
            mes_selecionado = hoje.replace(day=1)
    else:
        mes_selecionado = hoje.replace(day=1)

    # Buscar funcionários (não staff)
    funcionarios = User.objects.filter(is_staff=False).order_by('username')
    
    # Aplicar busca
    if busca:
        funcionarios = funcionarios.filter(
            Q(username__icontains=busca) | 
            Q(first_name__icontains=busca) | 
            Q(last_name__icontains=busca) |
            Q(email__icontains=busca)
        )

    # Calcular resumos
    dados = []
    total_pontos_mes = Decimal('0')
    total_bonus_mes = Decimal('0')
    
    for func in funcionarios:
        resumo = get_resumo_mes(func, mes_selecionado)
        dados.append(resumo)
        total_pontos_mes += resumo['pontos_liquidos']
        total_bonus_mes += resumo['bonus_reais']

    # Ordenação
    if ordenar == 'nome':
        dados.sort(key=lambda x: x['funcionario'].username)
    elif ordenar == 'bonus':
        dados.sort(key=lambda x: x['bonus_reais'], reverse=True)
    else:  # -pontos (default)
        dados.sort(key=lambda x: x['pontos_liquidos'], reverse=True)

    # Calcular média e totais
    if dados:
        media_pontos = total_pontos_mes / len(dados)
    else:
        media_pontos = Decimal('0')

    # Paginação (20 itens por página)
    paginator = Paginator(dados, 20)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'is_paginated': bool(dados),
        'mes_display': formatar_mes_pt(mes_selecionado),
        'mes_selecionado': mes_selecionado.strftime('%Y-%m'),
        'busca': busca,
        'ordenar': ordenar,
        'total_funcionarios': len(dados),
        'total_pontos_mes': total_pontos_mes.quantize(Decimal('0.01')),
        'total_bonus_mes': total_bonus_mes.quantize(Decimal('0.01')),
        'media_pontos': media_pontos.quantize(Decimal('0.01')),
    }
    return render(request, 'gamification/pontuacao.html', context)

@login_required
def bonus_view(request):
    if not (request.user.groups.filter(name__in=['Superadmin', 'Gerente']).exists() or request.user.is_superuser):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')

    faixas = BonusFaixa.objects.all().order_by('faixa_min')
    historico_bonus = HistoricoBonusMensal.objects.all().order_by('-mes_referencia')[:50]

    context = {
        'faixas': faixas,
        'historico_bonus': historico_bonus,
    }
    return render(request, 'gamification/bonus.html', context)