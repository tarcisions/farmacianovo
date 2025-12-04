from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from core.models import BonusFaixa, PontuacaoFuncionario, HistoricoBonusMensal
from django.utils import timezone
from django.db.models import Sum

@login_required
def pontuacao_view(request):
    if not (request.user.groups.filter(name__in=['Superadmin', 'Gerente']).exists() or request.user.is_superuser):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')

    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)

    funcionarios = User.objects.filter(groups__name='Funcionário')
    pontuacao_dados = []

    for func in funcionarios:
        pontos = PontuacaoFuncionario.pontos_mes_atual(func)
        historico = PontuacaoFuncionario.objects.filter(
            funcionario=func,
            mes_referencia__gte=primeiro_dia_mes
        ).order_by('-timestamp')[:5]

        pontuacao_dados.append({
            'funcionario': func,
            'pontos_mes': pontos,
            'historico': historico
        })

    context = {
        'pontuacao_dados': pontuacao_dados,
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