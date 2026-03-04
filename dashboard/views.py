# =========================
# Python
# =========================
import csv
import json
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
from itertools import groupby
from operator import attrgetter

# =========================
# Django
# =========================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q, Subquery, OuterRef, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse

# =========================
# Core Models
# =========================
from core.models import (
    Etapa,
    PedidoMestre,
    FormulaItem,
    PontuacaoFuncionario,
    BonusFaixa,
    HistoricoEtapaFormula,
    HistoricoBonusMensal,
    LogAuditoria,
    Penalizacao,
    PontuacaoFixaMensal,
    ControlePergunta,
    HistoricoControleQualidade,
    RespostaControleQualidade,
    ConfiguracaoControleQualidade,
)


def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    return redirect('login')

@login_required
def home(request):
    user_groups = request.user.groups.values_list('name', flat=True)
    
    if 'Funcionário' in user_groups:
        return redirect('dashboard:formulas_disponiveis')
    elif 'Gerente' in user_groups:
        return redirect('dashboard:gerente')
    elif 'Superadmin' in user_groups or request.user.is_superuser:
        return redirect('dashboard:superadmin')
    
    return redirect('login')

@login_required
def dashboard_funcionario(request):
    """Dashboard simplificado para funcionário"""

    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')

    # ===============================
    # BUSCAR TAREFAS ATIVAS
    # ===============================

    formulas_ativas = (
        FormulaItem.objects
        .filter(
            funcionario_na_etapa=request.user,
            status__in=['em_triagem', 'em_producao', 'em_qualidade']
        )
        .select_related('etapa_atual', 'pedido_mestre')
        .order_by('etapa_atual__nome', 'pedido_mestre__nrorc')
    )

    tarefas_totais = formulas_ativas.count()
    tarefas_ativas = formulas_ativas.filter(eh_tarefa_ativa=True).count()
    tarefas_pendentes = tarefas_totais - tarefas_ativas

    # ===============================
    # AGRUPAR POR ETAPA (FORMA PROFISSIONAL)
    # ===============================

    formulas_por_etapa = {
        etapa: list(items)
        for etapa, items in groupby(
            formulas_ativas,
            key=attrgetter('etapa_atual')
        )
    }

    # ===============================
    # HISTÓRICO DO DIA
    # ===============================

    hoje = timezone.now().date()

    historico_hoje = (
        HistoricoEtapaFormula.objects
        .filter(
            funcionario=request.user,
            timestamp_inicio__date=hoje
        )
        .select_related('etapa', 'formula')
    )

    formulas_completadas_hoje = historico_hoje.filter(
        timestamp_fim__date=hoje
    ).count()

    pontos_gerados_hoje = (
        historico_hoje.aggregate(total=Sum('pontos_gerados'))['total'] or 0
    )

    # ===============================
    # PONTOS DO MÊS
    # ===============================

    primeiro_dia_mes = hoje.replace(day=1)

    historico_mes = HistoricoEtapaFormula.objects.filter(
        funcionario=request.user,
        timestamp_inicio__gte=primeiro_dia_mes
    )

    pontos_mes = historico_mes.aggregate(
        total=Sum('pontos_gerados')
    )['total'] or 0

    # ===============================
    # TAXA DE CONCLUSÃO (últimas 10)
    # ===============================

    ultimas_formulas = (
        HistoricoEtapaFormula.objects
        .filter(funcionario=request.user)
        .values('formula')
        .distinct()
        .order_by('-timestamp_inicio')[:10]
    )

    if ultimas_formulas:
        concluidas = historico_hoje.filter(
            timestamp_fim__isnull=False
        ).count()

        taxa_conclusao = (concluidas / len(ultimas_formulas)) * 100
    else:
        taxa_conclusao = 0

    # ===============================
    # CONTEXT
    # ===============================

    context = {
        'tarefas_totais': tarefas_totais,
        'tarefas_ativas': tarefas_ativas,
        'tarefas_pendentes': tarefas_pendentes,
        'formulas_ativas': formulas_ativas,
        'formulas_por_etapa': formulas_por_etapa,  # agora já agrupado corretamente
        'formulas_completadas_hoje': formulas_completadas_hoje,
        'pontos_gerados_hoje': int(pontos_gerados_hoje),
        'pontos_mes': int(pontos_mes),
        'taxa_conclusao': int(taxa_conclusao),
    }

    return render(request, 'dashboard/dashboard_funcionario.html', context)

@login_required
def dashboard_gerente(request):
    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    
    # Filtros
    funcionario_id = request.GET.get('funcionario')
    status_filtro = request.GET.get('status')
    
    # Query base de pedidos mestres
    pedidos_query = PedidoMestre.objects.all()
    
    # Aplicar filtros
    if funcionario_id:
        # Filtrar por funcionários que trabalharam nas fórmulas do pedido
        pedidos_query = pedidos_query.filter(formulas__historico_etapas__funcionario_id=funcionario_id).distinct()
    if status_filtro:
        pedidos_query = pedidos_query.filter(status=status_filtro)
    
    pedidos_em_processamento = pedidos_query.filter(status='em_processamento').count()
    pedidos_concluidos_mes = pedidos_query.filter(
        status='concluido',
        concluido_em__gte=primeiro_dia_mes
    ).count()
    
    # Total de pontos distribuídos no mês
    total_pontos_distribuidos = PontuacaoFuncionario.objects.filter(
        mes_referencia__gte=primeiro_dia_mes
    ).aggregate(total=Sum('pontos'))['total'] or Decimal('0')
    
    funcionarios = User.objects.filter(groups__name='Funcionário')
    pontuacao_funcionarios = []
    
    for func in funcionarios:
        if funcionario_id and str(func.id) != funcionario_id:
            continue
            
        pontos = PontuacaoFuncionario.pontos_mes_atual(func)
        faixa = BonusFaixa.objects.filter(
            ativo=True,
            faixa_min__lte=pontos,
            faixa_max__gte=pontos
        ).first()
        
        pontuacao_funcionarios.append({
            'funcionario': func,
            'pontos': pontos,
            'faixa': faixa
        })
    
    pontuacao_funcionarios.sort(key=lambda x: x['pontos'], reverse=True)
    
    # Dados para os filtros
    todas_etapas = Etapa.objects.filter(ativa=True)
    todos_funcionarios = User.objects.filter(groups__name='Funcionário')
    
    context = {
        'pedidos_em_fluxo': pedidos_em_processamento,
        'pedidos_concluidos_mes': pedidos_concluidos_mes,
        'pontuacao_funcionarios': pontuacao_funcionarios,
        'todas_etapas': todas_etapas,
        'todos_funcionarios': todos_funcionarios,
        'funcionario_selecionado': funcionario_id,
        'status_selecionado': status_filtro,
        'total_pontos_distribuidos': total_pontos_distribuidos,
    }
    
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='outros',
        descricao='Acessou dashboard do gerente',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return render(request, 'dashboard/gerente.html', context)

@login_required
def penalizacoes_view(request):
    """Gestão de penalizações"""

    if not request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    # Filtros
    funcionario_id = request.GET.get('funcionario')
    
    penalizacoes = Penalizacao.objects.all().select_related('funcionario', 'aplicada_por', 'revertida_por')
    
    if funcionario_id:
        penalizacoes = penalizacoes.filter(funcionario_id=funcionario_id)
    
    penalizacoes = penalizacoes.order_by('-timestamp')
    
    # Lista de funcionários para o filtro
    funcionarios = User.objects.filter(groups__name='Funcionário')
    
    context = {
        'penalizacoes': penalizacoes,
        'funcionarios': funcionarios,
        'funcionario_selecionado': funcionario_id,
    }
    
    return render(request, 'dashboard/penalizacoes.html', context)

@login_required
def criar_penalizacao(request):
    """Criar nova penalização"""

    if not request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        funcionario_id = request.POST.get('funcionario_id')
        motivo = request.POST.get('motivo')
        pontos = request.POST.get('pontos')
        justificativa = request.POST.get('justificativa')
        
        try:
            funcionario = User.objects.get(id=funcionario_id, groups__name='Funcionário')
            pontos_decimal = Decimal(pontos)
            
            # Criar penalização
            penalizacao = Penalizacao.objects.create(
                funcionario=funcionario,
                motivo=motivo,
                pontos=pontos_decimal,
                justificativa=justificativa,
                aplicada_por=request.user
            )
            
            # Registrar pontuação negativa
            PontuacaoFuncionario.objects.create(
                funcionario=funcionario,
                pontos=-pontos_decimal,
                origem='penalizacao',
                mes_referencia=timezone.now().date(),
                observacao=f'Penalização: {motivo}'
            )
            
            LogAuditoria.objects.create(
                usuario=request.user,
                acao='penalizacao',
                descricao=f'Aplicou penalização de {pontos_decimal} pontos para {funcionario.get_full_name()} - Motivo: {motivo}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Penalização aplicada com sucesso!')
            return redirect('dashboard:penalizacoes')
            
        except Exception as e:
            messages.error(request, f'Erro ao aplicar penalização: {str(e)}')
            return redirect('dashboard:penalizacoes')
    
    funcionarios = User.objects.filter(groups__name='Funcionário')
    context = {
        'funcionarios': funcionarios,
    }
    return render(request, 'dashboard/criar_penalizacao.html', context)

@login_required
def reverter_penalizacao(request, penalizacao_id):
    """Reverter uma penalização"""
    
    if not request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    penalizacao = get_object_or_404(Penalizacao, id=penalizacao_id)
    
    if penalizacao.revertida:
        messages.warning(request, 'Esta penalização já foi revertida.')
        return redirect('dashboard:penalizacoes')
    
    # Reverter penalização
    penalizacao.revertida = True
    penalizacao.revertida_em = timezone.now()
    penalizacao.revertida_por = request.user
    penalizacao.save()
    
    # Adicionar pontos de volta
    PontuacaoFuncionario.objects.create(
        funcionario=penalizacao.funcionario,
        pontos=penalizacao.pontos,
        origem='penalizacao',
        mes_referencia=timezone.now().date(),
        observacao=f'Reversão de penalização: {penalizacao.motivo}'
    )
    
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='reverter_penalizacao',
        descricao=f'Reverteu penalização de {penalizacao.pontos} pontos de {penalizacao.funcionario.get_full_name()}',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    messages.success(request, 'Penalização revertida com sucesso!')
    return redirect('dashboard:penalizacoes')

@login_required
def lista_pedidos(request):
    """Lista PedidoMestre em andamento ou finalizados (expedidos)"""
    if not (request.user.groups.filter(name__in=['Superadmin', 'Gerente']).exists() or request.user.is_superuser):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    
    # Filtros
    nrorc_filtro = request.GET.get('nrorc', '')
    status_filtro = request.GET.get('status', '')
    mostrar_historico = request.GET.get('historico', '') == '1'
    
    # Query base - mostrar expedidos ou em andamento conforme filtro
    if mostrar_historico:
        # Em modo histórico, só mostrar expedidos, ignorar status_filtro
        pedidos = PedidoMestre.objects.filter(status='expedido').prefetch_related('formulas')
    else:
        # Em modo normal, mostrar não-expedidos
        pedidos = PedidoMestre.objects.exclude(status='expedido').prefetch_related('formulas')
        # Aplicar filtro de status apenas se não estiver em modo histórico
        if status_filtro:
            pedidos = pedidos.filter(status=status_filtro)
    
    # Aplicar filtro de NRORC em qualquer modo
    if nrorc_filtro:
        pedidos = pedidos.filter(nrorc__icontains=nrorc_filtro)
    
    pedidos = pedidos.order_by('-nrorc')
    
    # Paginação (20 itens por página)
    paginator = Paginator(pedidos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'pedidos': page_obj.object_list,
        'nrorc_filtro': nrorc_filtro,
        'status_filtro': status_filtro,
        'mostrar_historico': mostrar_historico,
    }
    
    return render(request, 'dashboard/pedidos.html', context)

@login_required
def exportar_relatorio_gerente(request):
    """Exporta relatório do gerente em CSV"""
    if not request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_gerente.csv"'
    response.write('\ufeff'.encode('utf-8'))  # BOM para Excel
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Funcionário', 'Pontos Mês Atual', 'Faixa de Bônus', 'Valor em Reais'])
    
    funcionarios = User.objects.filter(groups__name='Funcionário')
    for func in funcionarios:
        pontos = PontuacaoFuncionario.pontos_mes_atual(func)
        faixa = BonusFaixa.objects.filter(
            ativo=True,
            faixa_min__lte=pontos,
            faixa_max__gte=pontos
        ).first()
        
        writer.writerow([
            func.get_full_name() or func.username,
            str(pontos).replace('.', ','),
            f"{faixa.faixa_min}-{faixa.faixa_max}" if faixa else '-',
            str(faixa.valor_em_reais).replace('.', ',') if faixa else '0'
        ])
    
    return response

@login_required
def exportar_relatorio_superadmin(request):
    """Exporta relatório geral do sistema em CSV"""
    if not (request.user.groups.filter(name='Superadmin').exists() or request.user.is_superuser):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_sistema.csv"'
    response.write('\ufeff'.encode('utf-8'))  # BOM para Excel
    
    writer = csv.writer(response, delimiter=';')
    
    # Estatísticas gerais
    writer.writerow(['ESTATÍSTICAS GERAIS'])
    writer.writerow(['Total de Pedidos', PedidoMestre.objects.count()])
    writer.writerow(['Total de Usuários', User.objects.count()])
    writer.writerow(['Total de Etapas Ativas', Etapa.objects.filter(ativa=True).count()])
    writer.writerow([])
    
    # Pedidos por status
    writer.writerow(['PEDIDOS POR STATUS'])
    writer.writerow(['Status', 'Quantidade'])
    for item in PedidoMestre.objects.values('status').annotate(total=Count('id')):
        writer.writerow([dict(PedidoMestre.STATUS_CHOICES).get(item['status']), item['total']])
    writer.writerow([])
    
    # Ranking de funcionários
    writer.writerow(['RANKING DE FUNCIONÁRIOS'])
    writer.writerow(['Funcionário', 'Pontos Mês Atual', 'Faixa de Bônus'])
    funcionarios = User.objects.filter(groups__name='Funcionário')
    ranking = []
    for func in funcionarios:
        pontos = PontuacaoFuncionario.pontos_mes_atual(func)
        faixa = BonusFaixa.objects.filter(
            ativo=True,
            faixa_min__lte=pontos,
            faixa_max__gte=pontos
        ).first()
        ranking.append({
            'nome': func.get_full_name() or func.username,
            'pontos': pontos,
            'faixa': faixa
        })
    
    ranking.sort(key=lambda x: x['pontos'], reverse=True)
    for item in ranking:
        writer.writerow([
            item['nome'],
            str(item['pontos']).replace('.', ','),
            f"R$ {item['faixa'].valor_em_reais}" if item['faixa'] else '-'
        ])
    
    return response

@login_required
def perfil_funcionario(request, user_id):

    # ✅ Permitir apenas Gerente, Superadmin ou superuser
    if not (
        request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists()
        or request.user.is_superuser
    ):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')

    # Buscar funcionário obrigatoriamente pelo user_id
    usuario = get_object_or_404(
        User,
        pk=user_id,
        groups__name='Funcionário'
    )

    # Dados gerais
    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)

    # Pontos do mês atual
    pontos_mes_atual = PontuacaoFuncionario.pontos_mes_atual(usuario)

    # Faixa de bônus
    faixa_bonus = BonusFaixa.objects.filter(
        ativo=True,
        faixa_min__lte=pontos_mes_atual
    ).exclude(faixa_max__lt=pontos_mes_atual).first()

    bonus_em_reais = faixa_bonus.valor_em_reais if faixa_bonus else Decimal('0')

    # Histórico detalhado de pontos
    historico_pontos = PontuacaoFuncionario.objects.filter(
        funcionario=usuario,
        mes_referencia__gte=primeiro_dia_mes
    ).select_related('etapa').order_by('-timestamp')

    # Paginação
    paginator = Paginator(historico_pontos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Resumo por origem
    resumo_origem = historico_pontos.values('origem').annotate(
        total_pontos=Sum('pontos'),
        quantidade=Count('id')
    ).order_by('-total_pontos')

    # Resumo por etapa
    resumo_etapa = HistoricoEtapaFormula.objects.filter(
        funcionario=usuario,
        timestamp_fim__isnull=False,
        timestamp_inicio__gte=primeiro_dia_mes
    ).values('etapa__nome').annotate(
        total_pontos=Sum('pontos_gerados'),
        quantidade=Count('id')
    ).order_by('-total_pontos')

    # Penalizações do mês
    penalizacoes_mes = Penalizacao.objects.filter(
        funcionario=usuario,
        timestamp__gte=primeiro_dia_mes,
        revertida=False
    ).order_by('-timestamp')

    total_penalizacoes = penalizacoes_mes.aggregate(
        total=Sum('pontos')
    )['total'] or Decimal('0')

    # Últimos 12 meses
    ultimos_meses = []
    data_atual = hoje

    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    for _ in range(12):
        mes_data = data_atual - timedelta(days=data_atual.day - 1)

        pontos_do_mes = PontuacaoFuncionario.objects.filter(
            funcionario=usuario,
            mes_referencia__year=mes_data.year,
            mes_referencia__month=mes_data.month
        ).aggregate(total=Sum('pontos'))['total'] or Decimal('0')

        faixa_mes = BonusFaixa.objects.filter(
            ativo=True,
            faixa_min__lte=pontos_do_mes
        ).exclude(faixa_max__lt=pontos_do_mes).first()

        ultimos_meses.insert(0, {
            'mes': f"{meses_pt[mes_data.month]}/{mes_data.year}",
            'data': mes_data,
            'pontos': pontos_do_mes,
            'faixa': faixa_mes,
        })

        if mes_data.month == 1:
            data_atual = mes_data.replace(year=mes_data.year - 1, month=12)
        else:
            data_atual = mes_data.replace(month=mes_data.month - 1)

    # Estatísticas gerais
    total_pontos_todos_tempos = PontuacaoFuncionario.objects.filter(
        funcionario=usuario
    ).aggregate(total=Sum('pontos'))['total'] or Decimal('0')

    total_pedidos_trabalhados = FormulaItem.objects.filter(
        historico_etapas__funcionario=usuario
    ).distinct().count()

    # Etapas concluídas no mês
    etapas_concluidas = HistoricoEtapaFormula.objects.filter(
        funcionario=usuario,
        timestamp_fim__isnull=False,
        timestamp_inicio__gte=primeiro_dia_mes
    ).values('etapa__nome').annotate(
        total_pontos=Sum('pontos_gerados'),
        quantidade=Count('id')
    )

    # Evolução diária de pontos
    pontuacoes_mes = PontuacaoFuncionario.objects.filter(
        funcionario=usuario,
        mes_referencia__gte=primeiro_dia_mes
    ).order_by('timestamp').values('timestamp', 'pontos')

    pontos_por_dia = defaultdict(float)
    for p in pontuacoes_mes:
        dia = p['timestamp'].date()
        pontos_por_dia[dia] += float(p['pontos'])

    dias_mes = []
    acumulado = 0

    for dia in range(1, 32):
        try:
            data_dia = primeiro_dia_mes.replace(day=dia)
            if data_dia <= hoje:
                if data_dia in pontos_por_dia:
                    acumulado += pontos_por_dia[data_dia]
                dias_mes.append({
                    'dia': data_dia.strftime('%d/%m'),
                    'pontos': int(acumulado)
                })
        except ValueError:
            break

    if not dias_mes:
        dias_mes = [{
            'dia': hoje.strftime('%d/%m'),
            'pontos': int(pontos_mes_atual)
        }]

    dias_labels = json.dumps([d['dia'] for d in dias_mes])
    dias_data = json.dumps([d['pontos'] for d in dias_mes])

    context = {
        'usuario_perfil': usuario,
        'pontos_mes_atual': pontos_mes_atual,
        'faixa_bonus': faixa_bonus,
        'bonus_em_reais': bonus_em_reais,
        'page_obj': page_obj,
        'resumo_origem': resumo_origem,
        'resumo_etapa': resumo_etapa,
        'penalizacoes_mes': penalizacoes_mes,
        'total_penalizacoes': total_penalizacoes,
        'ultimos_meses': ultimos_meses,
        'total_pontos_todos_tempos': total_pontos_todos_tempos,
        'total_pedidos_trabalhados': total_pedidos_trabalhados,
        'etapas_concluidas': etapas_concluidas,
        'dias_labels': dias_labels,
        'dias_data': dias_data,
        'pedidos_trabalhados': total_pedidos_trabalhados,
    }

    return render(request, 'dashboard/perfil_funcionario.html', context)


@login_required
def lista_funcionarios(request):
    """Lista de funcionários com filtros e busca"""
    if not (request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() or request.user.is_superuser):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
        
    # Busca e filtros
    busca = request.GET.get('busca', '').strip()
    ordenar = request.GET.get('ordenar', '-pontos')  # -pontos, -data_joined, nome
    
    # Query base
    funcionarios = User.objects.filter(groups__name='Funcionário')
    
    # Aplicar busca
    if busca:
        funcionarios = funcionarios.filter(
            Q(username__icontains=busca) |
            Q(first_name__icontains=busca) |
            Q(last_name__icontains=busca) |
            Q(email__icontains=busca)
        )
    
    # Enriquecer dados com pontos
    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    
    func_data = []
    for func in funcionarios:
        pontos = PontuacaoFuncionario.pontos_mes_atual(func)
        func_data.append({
            'usuario': func,
            'pontos': pontos,
        })
    
    # Ordenar
    if ordenar == '-pontos':
        func_data.sort(key=lambda x: x['pontos'], reverse=True)
    elif ordenar == 'nome':
        func_data.sort(key=lambda x: (x['usuario'].first_name or x['usuario'].username).lower())
    elif ordenar == '-data_joined':
        func_data.sort(key=lambda x: x['usuario'].date_joined, reverse=True)
    
    # Paginação
    paginator = Paginator(func_data, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'is_paginated': bool(func_data),
        'busca': busca,
        'ordenar': ordenar,
    }
    
    return render(request, 'dashboard/lista_funcionarios.html', context)


@login_required
def dashboard_superadmin(request):
    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    
    total_pedidos = PedidoMestre.objects.count()
    total_usuarios = User.objects.count()
    total_etapas = Etapa.objects.filter(ativa=True).count()
    
    # Passar como list, o template tag json_script va fazer a serialização
    pedidos_por_status = list(PedidoMestre.objects.values('status').annotate(total=Count('id')))
    
    pontuacao_total_mes = PontuacaoFuncionario.objects.filter(
        mes_referencia__gte=primeiro_dia_mes
    ).aggregate(total=Sum('pontos'))['total'] or Decimal('0')
    
    logs_recentes = LogAuditoria.objects.all()[:50]
    
    context = {
        'total_pedidos': total_pedidos,
        'total_usuarios': total_usuarios,
        'total_etapas': total_etapas,
        'pedidos_por_status': pedidos_por_status,
        'pontuacao_total_mes': pontuacao_total_mes,
        'logs_recentes': logs_recentes,
    }
    
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='outros',
        descricao='Acessou dashboard do superadmin',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return render(request, 'dashboard/superadmin.html', context)

@login_required
def auditoria(request):
    """Tela de auditoria com logs completos"""
    
    # Verificar se é superadmin
    if not request.user.groups.filter(name='Superadmin').exists():
        messages.error(request, 'Você não tem permissão para acessar essa página.')
        return redirect('dashboard:home')
    
    # Filtros
    usuario_filtro = request.GET.get('usuario', '')
    acao_filtro = request.GET.get('acao', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    busca = request.GET.get('busca', '')
    
    # QuerySet base
    logs = LogAuditoria.objects.all().select_related('usuario').order_by('-timestamp')
    
    # Aplicar filtros
    if usuario_filtro:
        logs = logs.filter(usuario__username__icontains=usuario_filtro)
    
    if acao_filtro:
        logs = logs.filter(acao=acao_filtro)
    
    if data_inicio:
     
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
            logs = logs.filter(timestamp__date__gte=data_inicio_obj.date())
        except ValueError:
            pass
    
    if data_fim:
      
        try:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
            logs = logs.filter(timestamp__date__lte=data_fim_obj.date())
        except ValueError:
            pass
    
    if busca:
        logs = logs.filter(
            Q(descricao__icontains=busca) |
            Q(usuario__username__icontains=busca) |
            Q(ip_address__icontains=busca)
        )
    
    # Paginação
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page', 1)
    logs_paginados = paginator.get_page(page_number)
    
    # Opções de ações para filtro
    acoes_disponiveis = LogAuditoria.objects.values_list('acao', flat=True).distinct()
    
    context = {
        'logs': logs_paginados,
        'page_obj': logs_paginados,
        'is_paginated': bool(logs),
        'usuario_filtro': usuario_filtro,
        'acao_filtro': acao_filtro,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'busca': busca,
        'acoes_disponiveis': acoes_disponiveis,
        'total_logs': logs.count(),
    }
    
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='outros',
        descricao='Acessou tela de auditoria',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return render(request, 'dashboard/auditoria.html', context)

# Controle de Qualidade Views
from core.models import ControlePergunta, HistoricoControleQualidade, RespostaControleQualidade

@login_required
def controle_qualidade(request):
    """
    Listagem de Controle de Qualidade
    - Funcionários veem apenas seus próprios formulários
    - Gerentes/Admins veem todos os formulários de todos os funcionários
    """
    is_gerente = request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() or request.user.is_superuser
    
    # Determinar quais formulários mostrar
    if is_gerente:
        formularios = HistoricoControleQualidade.objects.select_related(
            'funcionario'
        ).prefetch_related(
            'respostas',
            'respostas__pergunta'
        ).order_by('-preenchido_em')
    else:
        # Funcionário vê apenas seus formulários
        formularios = HistoricoControleQualidade.objects.filter(
            funcionario=request.user
        ).select_related(
            'funcionario'
        ).prefetch_related(
            'respostas',
            'respostas__pergunta'
        ).order_by('-preenchido_em')
    
    # Processar filtros
    filtros = {
        'nome': '',
        'funcionario': '',
        'data_inicio': '',
        'data_fim': '',
    }
    
    # Filtro por nome ou código
    nome_filtro = request.GET.get('nome', '').strip()
    if nome_filtro:
        formularios = formularios.filter(
            Q(nome_item__icontains=nome_filtro) | Q(codigo_item__icontains=nome_filtro)
        )
        filtros['nome'] = nome_filtro
    
    # Filtro por funcionário (busca por nome)
    funcionario_filtro = request.GET.get('funcionario', '').strip()
    if funcionario_filtro:
        # Dividir o nome em partes para buscar melhor
        partes_nome = funcionario_filtro.split()
        
        query = Q()
        for parte in partes_nome:
            query |= (
                Q(funcionario__first_name__icontains=parte) | 
                Q(funcionario__last_name__icontains=parte) |
                Q(funcionario__username__icontains=parte)
            )
        
        formularios = formularios.filter(query)
        filtros['funcionario'] = funcionario_filtro
    
    # Filtro por intervalo de data
    data_inicio_filtro = request.GET.get('data_inicio', '').strip()
    data_fim_filtro = request.GET.get('data_fim', '').strip()
    
    if data_inicio_filtro:
      
        try:
            data_inicio = datetime.strptime(data_inicio_filtro, '%Y-%m-%d').date()
            formularios = formularios.filter(preenchido_em__date__gte=data_inicio)
            filtros['data_inicio'] = data_inicio_filtro
        except:
            pass
    
    if data_fim_filtro:
        
        try:
            data_fim = datetime.strptime(data_fim_filtro, '%Y-%m-%d').date()
            formularios = formularios.filter(preenchido_em__date__lte=data_fim)
            filtros['data_fim'] = data_fim_filtro
        except:
            pass
    
    # Paginação
    paginator = Paginator(formularios, 20)
    page_number = request.GET.get('page', 1)
    formularios_page = paginator.get_page(page_number)
    
    # Obter lista de funcionários para autocomplete
    funcionarios_lista = HistoricoControleQualidade.objects.values_list(
        'funcionario__first_name', 'funcionario__last_name', 'funcionario__username'
    ).distinct().order_by('funcionario__first_name')
    
    funcionarios_json = []
    for first_name, last_name, username in funcionarios_lista:
        nome_completo = f"{first_name} {last_name}".strip()
        if not nome_completo:
            nome_completo = username
        funcionarios_json.append({'nome': nome_completo})
    

    funcionarios_json = json.dumps(funcionarios_json)
    
    context = {
        'formularios': formularios_page,
        'page_obj': formularios_page,
        'is_paginated': bool(formularios),
        'total_formularios': formularios.count(),
        'is_gerente': is_gerente,
        'filtros': filtros,
        'funcionarios_json': funcionarios_json,
    }
    
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='outros',
        descricao='Acessou lista de Controle de Qualidade',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return render(request, 'dashboard/controle_qualidade.html', context)


@login_required
def controle_qualidade_detalhe(request, formulario_id):
    """
    Exibe os detalhes completos de um formulário de Controle de Qualidade
    """
    formulario = get_object_or_404(
        HistoricoControleQualidade.objects.prefetch_related(
            'respostas',
            'respostas__pergunta'
        ),
        id=formulario_id
    )
    
    # Verificar permissão: apenas o próprio funcionário ou gerente/admin pode ver
    is_gerente = request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() or request.user.is_superuser
    if not (request.user == formulario.funcionario or is_gerente):
        messages.error(request, 'Acesso negado')
        return redirect('dashboard:controle_qualidade')
    
    context = {
        'formulario': formulario,
    }
    
    return render(request, 'dashboard/controle_qualidade_detalhe.html', context)


@login_required
def controle_qualidade_formulario(request):
    """
    Formulário para preencher Controle de Qualidade (novo ou edição)
    Acessível para funcionários, gerentes e admins
    """
    # Obter todas as perguntas ativas ordenadas
    perguntas = ControlePergunta.objects.filter(
        ativo=True
    ).prefetch_related('opcoes').order_by('ordem', 'id')
    
    formulario = None
    respostas_salvas = []
    
    if request.method == 'POST':
        # Capturar dados do formulário
        nome_item = request.POST.get('nome_item', '').strip()
        codigo_item = request.POST.get('codigo_item', '').strip()
        
        # Validar campos obrigatórios
        if not nome_item:
            messages.error(request, 'Nome do item é obrigatório')
            context = {
                'perguntas': perguntas,
                'formulario': {'nome_item': nome_item, 'codigo_item': codigo_item},
                'respostas_salvas': respostas_salvas,
            }
            return render(request, 'dashboard/controle_qualidade_formulario.html', context)
        
        # Criar novo HistoricoControleQualidade com id_controle vazio
        formulario = HistoricoControleQualidade.objects.create(
            nome_item=nome_item,
            codigo_item=codigo_item,
            funcionario=request.user
        )
        
        # Atualizar id_controle com o ID do Django
        formulario.id_controle = str(formulario.id)
        formulario.save()
        
        # Processar cada pergunta
        for pergunta in perguntas:
            resposta_texto = request.POST.get(f'resposta_{pergunta.id}', '').strip()
            resposta_opcao_id = request.POST.get(f'opcao_{pergunta.id}')
            
            # Validar perguntas obrigatórias
            if pergunta.obrigatorio and not resposta_texto and not resposta_opcao_id:
                messages.error(request, f'A pergunta "{pergunta.pergunta}" é obrigatória')
                formulario.delete()
                context = {
                    'perguntas': perguntas,
                    'formulario': {'nome_item': nome_item, 'codigo_item': codigo_item},
                    'respostas_salvas': respostas_salvas,
                }
                return render(request, 'dashboard/controle_qualidade_formulario.html', context)
            
            # Salvar resposta
            resposta, _ = RespostaControleQualidade.objects.update_or_create(
                historico_controle=formulario,
                pergunta=pergunta,
                defaults={
                    'resposta_texto': resposta_texto,
                    'resposta_opcao_id': resposta_opcao_id if resposta_opcao_id else None,
                }
            )
        
        # Obter configuração de pontuação do Controle de Qualidade
        config = ConfiguracaoControleQualidade.get_configuracao_ativa()
        
        # Salvar pontuação total (baseada na configuração, não nas perguntas)
        formulario.pontuacao = config.pontos_por_formulario
        formulario.save()
        
        # Contabilizar pontos para o funcionário baseado na configuração
        config = ConfiguracaoControleQualidade.get_configuracao_ativa()
        
        PontuacaoFuncionario.objects.create(
            funcionario=request.user,
            pedido=None,
            etapa=None,
            pontos=config.pontos_por_formulario,
            origem='controle_qualidade',  # Nova origem
            mes_referencia=timezone.now().date(),
            observacao=f'Formulário CQ: {nome_item} (ID: {formulario.id_controle})'
        )
        
        messages.success(request, f'Formulário de Controle de Qualidade para "{nome_item}" salvo com sucesso!')
        
        LogAuditoria.objects.create(
            usuario=request.user,
            acao='outros',
            descricao=f'Preencheu Controle de Qualidade: ID {formulario.id_controle} - {nome_item} (+{config.pontos_por_formulario} pts)',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Redirecionar para a listagem
        return redirect('dashboard:controle_qualidade')
    
    context = {
        'perguntas': perguntas,
        'formulario': formulario,
        'respostas_salvas': respostas_salvas,
    }
    
    return render(request, 'dashboard/controle_qualidade_formulario.html', context)
