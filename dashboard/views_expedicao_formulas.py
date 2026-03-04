"""
Views para expedição do novo fluxo com Fórmulas (FormulaItem)
Criado para o sistema de múltiplas fórmulas por pedido
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator

from core.models import (
    PedidoMestre, FormulaItem, Etapa, HistoricoEtapaFormula,
    PontuacaoFuncionario, LogAuditoria
)


@login_required
def pedidos_prontos_expedicao(request):
    """
    Lista pedidos mestres prontos para expedição.
    Apenas funcionários do grupo 'Expedição' podem acessar.
    """
    if not request.user.groups.filter(name='Expedição').exists():
        return redirect('dashboard:home')
    
    # Obter filtros
    nrorc = request.GET.get('nrorc', '').strip()
    rota_tipo = request.GET.get('rota_tipo', '').strip()
    
    # Buscar pedidos mestres prontos para expedição
    pedidos = PedidoMestre.objects.filter(
        status='pronto_para_expedicao'
    ).select_related().prefetch_related('formula_set')
    
    if nrorc:
        pedidos = pedidos.filter(nrorc__icontains=nrorc)
    
    # Paginação
    paginator = Paginator(pedidos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filtro_nrorc': nrorc,
        'filtro_rota_tipo': rota_tipo,
        'ROTA_CHOICES': ['motoboy', 'sedex'],
    }
    
    return render(request, 'dashboard/pedidos_prontos_expedicao.html', context)


@login_required
def detalhe_pedido_expedicao(request, pedido_id):
    """
    Mostra detalhes de um pedido mestre para expedição.
    Permite selecionar tipo de rota e executar expedição.
    """
    if not request.user.groups.filter(name='Expedição').exists():
        return redirect('dashboard:home')
    
    pedido = get_object_or_404(
        PedidoMestre.objects.prefetch_related('formula_set'),
        id=pedido_id
    )
    
    # Validar se está pronto
    if pedido.status != 'pronto_para_expedicao':
        messages.error(request, 'Este pedido não está pronto para expedição.')
        return redirect('dashboard:pedidos_prontos_expedicao')
    
    # Obter todas as fórmulas
    formulas = pedido.formula_set.all()
    
    context = {
        'pedido': pedido,
        'formulas': formulas,
        'ROTA_CHOICES': ['motoboy', 'sedex'],
    }
    
    return render(request, 'dashboard/detalhe_pedido_expedicao.html', context)


@login_required
@transaction.atomic
def executar_expedicao(request, pedido_id):
    """
    Executa a expedição de um pedido mestre.
    Cria histórico de etapa para a expedição e marca pedido como concluído.
    """
    if request.method != 'POST':
        return redirect('dashboard:pedidos_prontos_expedicao')
    
    if not request.user.groups.filter(name='Expedição').exists():
        return redirect('dashboard:home')
    
    pedido = get_object_or_404(PedidoMestre, id=pedido_id)
    
    # Validações
    if pedido.status != 'pronto_para_expedicao':
        messages.error(request, 'Este pedido não está pronto para expedição.')
        return redirect('dashboard:pedidos_prontos_expedicao')
    
    # Obter tipo de rota
    rota_tipo = request.POST.get('rota_tipo', '').strip()
    if rota_tipo not in ['motoboy', 'sedex']:
        messages.error(request, 'Tipo de rota inválido.')
        return redirect('dashboard:detalhe_pedido_expedicao', pedido_id=pedido.id)
    
    # Obter etapa de expedição
    try:
        etapa_expedicao = Etapa.objects.get(nome__icontains='expedição')
    except Etapa.DoesNotExist:
        messages.error(request, 'Etapa de expedição não configurada.')
        return redirect('dashboard:detalhe_pedido_expedicao', pedido_id=pedido.id)
    
    # Processar cada fórmula do pedido
    formulas = pedido.formula_set.filter(status='pronto_para_expedicao')
    
    if not formulas.exists():
        messages.error(request, 'Nenhuma fórmula pronta para expedição neste pedido.')
        return redirect('dashboard:detalhe_pedido_expedicao', pedido_id=pedido.id)
    
    try:
        for formula in formulas:
            # Criar histórico de expedição
            HistoricoEtapaFormula.objects.create(
                formula=formula,
                etapa=etapa_expedicao,
                funcionario=request.user,
                rota_tipo=rota_tipo,
                pontos_gerados=etapa_expedicao.pontos_fixos_etapa or 0,
            )
            
            # Marcar fórmula como expedida
            formula.status = 'expedido'
            formula.concluido_em = timezone.now()
            formula.etapa_atual = None
            formula.save()
            
            # Adicionar pontos para quem executou a expedição
            PontuacaoFuncionario.objects.create(
                funcionario=request.user,
                etapa=etapa_expedicao,
                pontos=etapa_expedicao.pontos_fixos_etapa or 0,
                origem='expedição',
                mes_referencia=timezone.now().date().replace(day=1),
            )
        
        # Atualizar status do pedido mestre
        pedido.status = 'concluido'
        pedido.concluido_em = timezone.now()
        pedido.save()
        
        # Log de auditoria
        LogAuditoria.objects.create(
            usuario=request.user,
            acao='expedicao',
            descricao=f'Expediu pedido NRORC {pedido.nrorc} via {rota_tipo}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(
            request,
            f'Pedido NRORC {pedido.nrorc} foi expedido com sucesso! ({len(formulas)} fórmula(s))'
        )
        
        return redirect('dashboard:pedidos_prontos_expedicao')
    
    except Exception as e:
        messages.error(request, f'Erro ao executar expedição: {str(e)}')
        return redirect('dashboard:detalhe_pedido_expedicao', pedido_id=pedido.id)
