"""
Views para o novo fluxo com Fórmulas (FormulaItem)
Criado para o sistema de múltiplas fórmulas por pedido
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
from datetime import datetime

from core.models import (
    FormulaItem, PedidoMestre, Etapa, HistoricoEtapaFormula,
    PontuacaoFuncionario, LogAuditoria, Checklist, ChecklistExecucaoFormula
)


@login_required
def formulas_disponiveis(request):
    """Lista fórmulas disponíveis para assumir (novo fluxo)"""
    is_funcionario = request.user.groups.filter(name='Funcionário').exists()
    is_gestor = request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() or request.user.is_superuser
    
    if not (is_funcionario or is_gestor):
        return redirect('dashboard:home')
    
    # Filtros
    nrorc = request.GET.get('nrorc', '').strip()
    descricao = request.GET.get('descricao', '').strip()
    etapa_id = request.GET.get('etapa', '')
    pedido_mestre_id = request.GET.get('pedido_mestre', '').strip()
    
    # Buscar fórmulas
    if is_funcionario:
        # Funcionários veem apenas fórmulas disponíveis (sem funcionário)
        formulas = FormulaItem.objects.filter(
            funcionario_na_etapa__isnull=True,
            status__in=['em_triagem', 'em_producao', 'em_qualidade']
        ).select_related('pedido_mestre', 'etapa_atual').order_by('-datetime_atualizacao_api', '-criado_em')
    else:
        # Gerentes/Admins veem todas as fórmulas (auditoria)
        formulas = FormulaItem.objects.all().select_related('pedido_mestre', 'etapa_atual').order_by('-datetime_atualizacao_api', '-criado_em')
    
    if nrorc:
        formulas = formulas.filter(pedido_mestre__nrorc__icontains=nrorc)
    if descricao:
        formulas = formulas.filter(descricao__icontains=descricao)
    if etapa_id:
        formulas = formulas.filter(etapa_atual_id=etapa_id)
    if pedido_mestre_id:
        formulas = formulas.filter(pedido_mestre_id=pedido_mestre_id)
    
    # Paginação
    paginator = Paginator(formulas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    etapas = Etapa.objects.filter(ativa=True).order_by('sequencia')
    
    context = {
        'page_obj': page_obj,
        'etapas': etapas,
        'filtro_nrorc': nrorc,
        'filtro_descricao': descricao,
        'filtro_etapa': etapa_id,
        'is_funcionario': is_funcionario,
        'is_gestor': is_gestor,
    }
    
    return render(request, 'dashboard/formulas_disponiveis.html', context)


@login_required
def minhas_formulas(request):
    """Fórmulas que o funcionário está trabalhando atualmente"""
    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')
    
    # Buscar todas as fórmulas do funcionário
    formulas = FormulaItem.objects.filter(
        funcionario_na_etapa=request.user,
        status__in=['em_triagem', 'em_producao', 'em_qualidade']
    ).select_related('pedido_mestre', 'etapa_atual').order_by('etapa_atual', '-eh_tarefa_ativa', '-datetime_atualizacao_api', '-criado_em')
    
    # Agrupar por etapa para melhor visualização
    formulas_por_etapa = {}
    for formula in formulas:
        etapa_nome = formula.etapa_atual.nome if formula.etapa_atual else 'Sem Etapa'
        if etapa_nome not in formulas_por_etapa:
            formulas_por_etapa[etapa_nome] = {'ativa': [], 'pendentes': []}
        
        if formula.eh_tarefa_ativa:
            formulas_por_etapa[etapa_nome]['ativa'].append(formula)
        else:
            formulas_por_etapa[etapa_nome]['pendentes'].append(formula)
    
    # Contar total de tarefas
    total_tarefas = formulas.count()
    tarefas_ativas = formulas.filter(eh_tarefa_ativa=True).count()
    tarefas_pendentes = total_tarefas - tarefas_ativas
    
    context = {
        'formulas_por_etapa': formulas_por_etapa,
        'formulas': formulas,
        'total_tarefas': total_tarefas,
        'tarefas_ativas': tarefas_ativas,
        'tarefas_pendentes': tarefas_pendentes,
    }
    
    return render(request, 'dashboard/minhas_formulas.html', context)


@login_required
def pausar_tarefa_formula(request, formula_id):
    """Pausa a tarefa ativa e ativa a primeira pendente se existir"""
    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')
    
    formula = get_object_or_404(FormulaItem, id=formula_id, funcionario_na_etapa=request.user)
    
    if not formula.eh_tarefa_ativa:
        messages.error(request, 'Esta tarefa não está ativa para ser pausada.')
        return redirect('dashboard:minhas_formulas')
    
    # Pausa a tarefa ativa
    formula.eh_tarefa_ativa = False
    formula.save()
    
    # Buscar primeira tarefa pendente NESTA MESMA ETAPA para ativar
    proxima_pendente = FormulaItem.objects.filter(
        funcionario_na_etapa=request.user,
        etapa_atual=formula.etapa_atual,
        eh_tarefa_ativa=False,
        status__in=['em_triagem', 'em_producao', 'em_qualidade']
    ).first()
    
    if proxima_pendente:
        proxima_pendente.eh_tarefa_ativa = True
        proxima_pendente.save()
        messages.info(request, f'✓ Tarefa pausada! Tarefa NRORC {proxima_pendente.pedido_mestre.nrorc} agora está ATIVA.')
    else:
        messages.success(request, f'✓ Tarefa NRORC {formula.pedido_mestre.nrorc} pausada com sucesso!')
    
    # Log
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='pausar_tarefa',
        descricao=f'Pausou tarefa NRORC {formula.pedido_mestre.nrorc} na etapa {formula.etapa_atual.nome}',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return redirect('dashboard:minhas_formulas')


@login_required
def ativar_tarefa_formula(request, formula_id):
    """Ativa uma tarefa pendente (se houver ativa, pausa ela primeiro)"""
    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')
    
    formula = get_object_or_404(FormulaItem, id=formula_id, funcionario_na_etapa=request.user)
    
    if formula.eh_tarefa_ativa:
        messages.error(request, 'Esta tarefa já está ativa.')
        return redirect('dashboard:minhas_formulas')
    
    # Verificar se já tem uma tarefa ATIVA NESTA ETAPA
    ativa_etapa = FormulaItem.objects.filter(
        funcionario_na_etapa=request.user,
        etapa_atual=formula.etapa_atual,
        eh_tarefa_ativa=True
    ).first()
    
    if ativa_etapa:
        # Pausa a ativa
        ativa_etapa.eh_tarefa_ativa = False
        ativa_etapa.save()
        mensagem_pausa = f' (NRORC {ativa_etapa.pedido_mestre.nrorc} foi pausada)'
    else:
        mensagem_pausa = ''
    
    # Ativa a pendente
    formula.eh_tarefa_ativa = True
    formula.save()
    
    messages.success(request, f'✓ Tarefa NRORC {formula.pedido_mestre.nrorc} agora está ATIVA!{mensagem_pausa}')
    
    # Log
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='ativar_tarefa',
        descricao=f'Ativou tarefa NRORC {formula.pedido_mestre.nrorc} na etapa {formula.etapa_atual.nome}',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return redirect('dashboard:minhas_formulas')


@login_required
def assumir_formula(request, formula_id):
    """Assume uma fórmula para trabalhar"""
    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')
    
    formula = get_object_or_404(FormulaItem, id=formula_id)
    
    # Validações
    if formula.funcionario_na_etapa:
        messages.error(request, 'Esta fórmula já foi assumida por outro funcionário.')
        return redirect('dashboard:formulas_disponiveis')
    
    if formula.status not in ['em_triagem', 'em_producao', 'em_qualidade']:
        messages.error(request, 'Esta fórmula não está disponível para ser assumida.')
        return redirect('dashboard:formulas_disponiveis')
    
    # Limitar a 5 fórmulas simultâneas (ativo + pendentes)
    if formula.etapa_atual and formula.etapa_atual.nome.lower() != 'expedição':
        tarefas_totais = FormulaItem.objects.filter(
            funcionario_na_etapa=request.user,
            status__in=['em_triagem', 'em_producao', 'em_qualidade'],
            eh_tarefa_ativa__in=[True, False]  # Ambos ativo e pendente
        ).count()
        
        if tarefas_totais >= 5:
            messages.error(request, 'Você atingiu o máximo de 5 tarefas. Conclua ou pause uma tarefa antes de assumir outra.')
            return redirect('dashboard:formulas_disponiveis')
        
        # Verificar se já tem 1 tarefa ativa nesta etapa
        tem_ativa_etapa = FormulaItem.objects.filter(
            funcionario_na_etapa=request.user,
            etapa_atual=formula.etapa_atual,
            eh_tarefa_ativa=True
        ).exists()
        
        # Se não tem ativa nesta etapa, esta será ativa. Senão será pendente.
        nova_tarefa_ativa = not tem_ativa_etapa
    else:
        nova_tarefa_ativa = False  # Expedição não usa sistema de ativo/pendente
    
    # Assumir
    formula.funcionario_na_etapa = request.user
    formula.eh_tarefa_ativa = nova_tarefa_ativa
    formula.save()
    
    # Log
    status_log = "ativa" if nova_tarefa_ativa else "pendente"
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='assumir_etapa',
        descricao=f'Assumiu fórmula NRORC {formula.pedido_mestre.nrorc} na etapa {formula.etapa_atual.nome} ({status_log})',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    if nova_tarefa_ativa:
        messages.success(request, f'✓ Fórmula NRORC {formula.pedido_mestre.nrorc} assumida como ATIVA!')
    else:
        messages.info(request, f'✓ Fórmula NRORC {formula.pedido_mestre.nrorc} adicionada como PENDENTE. Pause sua tarefa ativa para começar.')
    
    # Redirecionar para tela de trabalho da fórmula
    return redirect('dashboard:detalhe_formula', formula_id=formula.id)


@login_required
def detalhe_formula(request, formula_id):
    """Exibe detalhes da fórmula e permite trabalhar nela"""
    # Permitir funcionários e gerentes/admins
    is_funcionario = request.user.groups.filter(name='Funcionário').exists()
    is_gestor = request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() or request.user.is_superuser
    
    if not (is_funcionario or is_gestor):
        return redirect('dashboard:home')
    
    formula = get_object_or_404(
        FormulaItem.objects.select_related('pedido_mestre', 'etapa_atual'),
        id=formula_id
    )
    
    # Permissão: funcionários só podem ver suas fórmulas, gerentes podem ver tudo
    if is_funcionario and formula.funcionario_na_etapa != request.user:
        messages.error(request, 'Você não tem permissão para acessar esta fórmula.')
        return redirect('dashboard:minhas_formulas')
    
    # Obter checklists da etapa atual
    checklists = Checklist.objects.filter(
        etapa=formula.etapa_atual,
        ativo=True
    ).order_by('ordem')
    
    # Histórico desta fórmula nesta etapa
    historico_etapa = HistoricoEtapaFormula.objects.filter(
        formula=formula,
        etapa=formula.etapa_atual
    ).first()
    
    # Se for funcionário, criar histórico no primeiro acesso
    if is_funcionario:
        if not historico_etapa:
            # Criar histórico (primeiro acesso)
            historico_etapa = HistoricoEtapaFormula.objects.create(
                formula=formula,
                etapa=formula.etapa_atual,
                funcionario=request.user,
            )
    
    # Sincronizar execuções de checklists (apenas ativos)
    if historico_etapa:
        # Criar/manter executações apenas para checklists ativos
        for chk in checklists:
            execucao, created = ChecklistExecucaoFormula.objects.get_or_create(
                historico_etapa=historico_etapa,
                checklist=chk,
                defaults={'marcado': False, 'pontos_gerados': chk.pontos_do_check}
            )
            # Atualizar pontos_gerados em caso de edição
            if execucao.pontos_gerados != chk.pontos_do_check:
                execucao.pontos_gerados = chk.pontos_do_check
                execucao.save()
        
        # Remover execuções de checklists desativados
        ChecklistExecucaoFormula.objects.filter(
            historico_etapa=historico_etapa
        ).exclude(
            checklist__in=checklists
        ).delete()
    
    # Execuções de checklist
    checklist_execucoes = ChecklistExecucaoFormula.objects.filter(
        historico_etapa=historico_etapa
    ) if historico_etapa else []
    
    # Mapear checklist_id -> marcado para facilitar no template
    checklist_marcados = {exec.checklist_id: exec.marcado for exec in checklist_execucoes}
    
    context = {
        'formula': formula,
        'historico_etapa': historico_etapa,
        'checklists': checklists,
        'checklist_execucoes': checklist_execucoes,
        'checklist_marcados': checklist_marcados,
        'etapa_atual': formula.etapa_atual,
        'is_gestor': is_gestor,
        'is_funcionario': is_funcionario,
    }
    
    return render(request, 'dashboard/detalhe_formula.html', context)


@login_required
def marcar_checklist_formula(request, formula_id, checklist_id):
    """Marca um checklist como executado em uma fórmula - retorna JSON"""
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)
    
    formula = get_object_or_404(FormulaItem, id=formula_id)
    checklist = get_object_or_404(Checklist, id=checklist_id)
    
    # Verificar permissão
    is_funcionario = request.user.groups.filter(name='Funcionário').exists()
    is_gestor = request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() or request.user.is_superuser
    
    if not (is_funcionario or is_gestor):
        return JsonResponse({'erro': 'Sem permissão'}, status=403)
    
    # Obter histórico
    historico = HistoricoEtapaFormula.objects.filter(
        formula=formula,
        etapa=formula.etapa_atual
    ).first()
    
    if not historico:
        return JsonResponse({'erro': 'Histórico não encontrado'}, status=404)
    
    # Verificar permissão do funcionário
    if is_funcionario and historico.funcionario != request.user:
        return JsonResponse({'erro': 'Sem permissão para esta fórmula'}, status=403)
    
    # Marcar/desmarcar
    execucao, created = ChecklistExecucaoFormula.objects.get_or_create(
        historico_etapa=historico,
        checklist=checklist,
        defaults={'marcado': False, 'pontos_gerados': checklist.pontos_do_check}
    )
    
    execucao.marcado = not execucao.marcado
    if execucao.marcado:
        execucao.marcado_em = timezone.now()
    else:
        execucao.marcado_em = None
    execucao.save()
    
    # Log
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='marcar_checklist',
        descricao=f'{"Marcou" if execucao.marcado else "Desmarcou"} {checklist.nome}',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return JsonResponse({
        'sucesso': True,
        'marcado': execucao.marcado,
        'checklist_id': checklist_id
    })


@login_required
def finalizar_etapa_formula(request, formula_id):
    """Finaliza uma fórmula em sua etapa atual e avança para próxima"""
    import logging
    logger = logging.getLogger('django')
    
    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')
    
    formula = get_object_or_404(FormulaItem, id=formula_id)
    
    # Permissão: apenas funcionário responsável pode finalizar
    if formula.funcionario_na_etapa != request.user:
        messages.error(request, 'Você não tem permissão para finalizar esta fórmula.')
        return redirect('dashboard:minhas_formulas')
    
    etapa = formula.etapa_atual
    if not etapa:
        messages.error(request, 'Fórmula sem etapa atual.')
        return redirect('dashboard:minhas_formulas')
    
    historico = HistoricoEtapaFormula.objects.filter(
        formula=formula,
        etapa=etapa
    ).first()
    
    if not historico:
        messages.error(request, 'Histórico não encontrado.')
        return redirect('dashboard:detalhe_formula', formula_id=formula.id)
    
    # ----------------------------
    # Sincronizar execuções de checklists (apenas ativos)
    # ----------------------------
    checklists_ativos = Checklist.objects.filter(etapa=etapa, ativo=True)
    
    # Criar executações apenas para checklists ativos
    for chk in checklists_ativos:
        execucao, created = ChecklistExecucaoFormula.objects.get_or_create(
            historico_etapa=historico,
            checklist=chk,
            defaults={'marcado': False, 'pontos_gerados': chk.pontos_do_check}
        )
        # Atualizar pontos_gerados em caso de edição no checklist
        if execucao.pontos_gerados != chk.pontos_do_check:
            execucao.pontos_gerados = chk.pontos_do_check
            execucao.save()
    
    # Remover execuções de checklists desativados ou deletados
    ChecklistExecucaoFormula.objects.filter(
        historico_etapa=historico
    ).exclude(
        checklist__in=checklists_ativos
    ).delete()
    
    # ----------------------------
    # Validar checklists obrigatórios
    # ----------------------------
    # Contar apenas checklists que são OBRIGATÓRIOS AGORA e não foram marcados
    checklists_obrigatorios_ativos = checklists_ativos.filter(obrigatorio=True)
    
    logger.info(f'finalizar_etapa: checklists_ativos={list(checklists_ativos.values_list("nome", "obrigatorio"))}')
    logger.info(f'finalizar_etapa: checklists_obrigatorios_ativos={list(checklists_obrigatorios_ativos.values_list("nome"))}')
    
    nao_marcados_obrigatorios = ChecklistExecucaoFormula.objects.filter(
        historico_etapa=historico,
        checklist__in=checklists_obrigatorios_ativos,
        marcado=False
    )
    
    logger.info(f'finalizar_etapa: nao_marcados_obrigatorios={list(nao_marcados_obrigatorios.values_list("checklist__nome", "marcado"))}')
    logger.info(f'finalizar_etapa: nao_marcados_obrigatorios.exists()={nao_marcados_obrigatorios.exists()}')
    
    if nao_marcados_obrigatorios.exists():
        lista_faltantes = ', '.join([exe.checklist.nome for exe in nao_marcados_obrigatorios])
        total = nao_marcados_obrigatorios.count()
        logger.warning(f'finalizar_etapa: BLOQUEADO! Faltam {total} checklists')
        messages.error(
            request,
            f'Faltam {total} checklist(s) obrigatório(s): {lista_faltantes}'
        )
        return redirect('dashboard:detalhe_formula', formula_id=formula.id)
    
    logger.info(f'finalizar_etapa: Validação passou! Continuando com finalização')
    
    # ----------------------------
    # Calcular pontos gerados
    # ----------------------------
    aggregado = ChecklistExecucaoFormula.objects.filter(
        historico_etapa=historico,
        marcado=True
    ).aggregate(total=Sum('pontos_gerados'))
    pontos_checklists = aggregado.get('total') or Decimal('0')
    
    pontos_fixos = etapa.pontos_fixos_etapa if etapa else Decimal('0')
    total_pontos = Decimal(str(pontos_checklists)) + Decimal(str(pontos_fixos))
    
    historico.timestamp_fim = timezone.now()
    historico.pontos_gerados = total_pontos
    historico.save()
    
    # Registrar pontuação do funcionário
    PontuacaoFuncionario.objects.create(
        funcionario=request.user,
        etapa=etapa,
        pontos=total_pontos,
        origem='etapa',
        mes_referencia=timezone.now().date().replace(day=1),
    )
    
    # ----------------------------
    # Avançar etapa
    # ----------------------------
    proxima_etapa = etapa.proxima_etapa() if etapa else None
    
    if proxima_etapa:
        formula.etapa_atual = proxima_etapa
        # Atualizar status da fórmula
        nome_lower = proxima_etapa.nome.lower()
        if 'triagem' in nome_lower:
            formula.status = 'em_triagem'
        elif 'produção' in nome_lower:
            formula.status = 'em_producao'
        elif 'qualidade' in nome_lower:
            formula.status = 'em_qualidade'
        elif 'expedição' in nome_lower:
            formula.status = 'pronto_para_expedicao'
    else:
        # Sem próxima etapa - fórmula expedida
        formula.status = 'expedido'
        formula.etapa_atual = None
        formula.concluido_em = timezone.now()
    
    # Limpar funcionário da etapa
    formula.funcionario_na_etapa = None
    formula.save()
    
    # Validar PedidoMestre
    formula.pedido_mestre.validar_e_atualizar_status()
    
    # Log de auditoria
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='concluir_etapa',
        descricao=f'Finalizou fórmula NRORC {formula.pedido_mestre.nrorc}' +
                  (f' na etapa {formula.etapa_atual.nome}' if formula.etapa_atual else ''),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    messages.success(request, 'Fórmula finalizada com sucesso!')
    
    # Mensagem extra se chegou na expedição
    if formula.status == 'expedido':
        messages.info(request, f'Fórmula NRORC {formula.pedido_mestre.nrorc} pronta para expedição!')
    
    return redirect('dashboard:minhas_formulas')


@login_required
def formulas_expedicao_funcionario(request):
    """
    Lista pedidos mestres com fórmulas prontas para expedição
    Funcionário escolhe a rota (motoboy ou sedex) para o PEDIDO COMPLETO
    """
    # Apenas funcionários
    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')
    
    # Buscar todos os pedidos mestres que têm fórmulas prontas para expedição
    # E que foram finalizadas por este funcionário
    pedidos = PedidoMestre.objects.filter(
        formulas__status='pronto_para_expedicao',
        formulas__historico_etapas__funcionario=request.user
    ).distinct().select_related().prefetch_related('formulas')
    
    # Filtrar apenas os que estão prontos e ainda não foram expedidos
    pedidos = pedidos.filter(status__in=['pronto_para_expedicao', 'em_processamento'])
    
    # Paginação
    paginator = Paginator(pedidos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Para cada pedido, contar as fórmulas prontas para expedição
    pedidos_com_count = []
    for pedido in page_obj:
        formulas_prontas = pedido.formulas.filter(status='pronto_para_expedicao').count()
        pedidos_com_count.append({
            'pedido': pedido,
            'formulas_prontas': formulas_prontas,
        })
    
    context = {
        'page_obj': page_obj,
        'pedidos_com_count': pedidos_com_count,
        'titulo': 'Expedição de Pedidos',
        'descricao': 'Selecione a rota de expedição para cada pedido completo',
    }
    
    return render(request, 'dashboard/formulas_expedicao.html', context)


@login_required
def pedido_escolher_rota(request, pedido_id, rota_tipo):
    """Marca pedido para uma rota (ainda não finalizado - vai ficar em fila de espera)"""
    if rota_tipo not in ['motoboy', 'sedex']:
        messages.error(request, 'Rota inválida.')
        return redirect('dashboard:rotas_unificada')
    
    pedido = get_object_or_404(PedidoMestre, id=pedido_id)
    
    # Buscar todas as fórmulas prontas para expedição deste pedido
    formulas = FormulaItem.objects.filter(
        pedido_mestre=pedido,
        status='pronto_para_expedicao'
    )
    
    if not formulas.exists():
        messages.error(request, 'Este pedido não tem fórmulas prontas para expedição.')
        return redirect('dashboard:rotas_unificada')
    
    # Verificar se este funcionário trabalhou em alguma das fórmulas
    trabalhou = False
    for formula in formulas:
        if HistoricoEtapaFormula.objects.filter(formula=formula, funcionario=request.user).exists():
            trabalhou = True
            break
    
    if not trabalhou:
        messages.error(request, 'Você não tem permissão para continuar com este pedido.')
        return redirect('dashboard:rotas_unificada')
    
    # Marcar pedido como "em_rota_motoboy" ou "em_rota_sedex" (não como expedido!)
    status_rota = f'em_rota_{rota_tipo}'
    pedido.status = status_rota
    pedido.save()
    
    # Log da ação
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='marcar_rota',
        descricao=f'Marcou pedido NRORC {pedido.nrorc} para rota {rota_tipo.upper()} ({formulas.count()} fórmulas)',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    messages.success(request, f'✓ Pedido NRORC {pedido.nrorc} adicionado à rota {rota_tipo.upper()}! Selecione mais pedidos ou envie agora.')
    # Redireciona para o tab da rota (motoboy ou sedex) - NÃO para detalhes
    return redirect('dashboard:rotas_unificada')


@login_required
def formula_escolher_rota(request, formula_id, rota_tipo):
    """Registra a escolha de rota (motoboy ou sedex) para uma fórmula"""
    if rota_tipo not in ['motoboy', 'sedex']:
        messages.error(request, 'Rota inválida.')
        return redirect('dashboard:formulas_expedicao')
    
    formula = get_object_or_404(FormulaItem, id=formula_id, status='pronto_para_expedicao')
    
    # Verificar se este funcionário trabalhou nesta fórmula
    if not HistoricoEtapaFormula.objects.filter(formula=formula, funcionario=request.user).exists():
        messages.error(request, 'Você não tem permissão para continuar com esta fórmula.')
        return redirect('dashboard:formulas_expedicao')
    
    # Atualizar status para expedido e criar log
    formula.status = 'expedido'
    formula.save()
    
    # Registrar escolha de rota no histórico
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='expedir_formula',
        descricao=f'Expediu fórmula NRORC {formula.pedido_mestre.nrorc} via {rota_tipo.upper()}',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    messages.success(request, f'Fórmula NRORC {formula.pedido_mestre.nrorc} enviada por {rota_tipo.upper()} com sucesso!')
    return redirect('dashboard:formulas_expedicao')


@login_required
def historico_etapas_formula(request, formula_id):
    """Exibe o histórico de etapas de uma fórmula com funcionários e tempos"""
    formula = get_object_or_404(FormulaItem, id=formula_id)
    
    # Permissão: qualquer um pode visualizar
    if not request.user.groups.filter(name__in=['Funcionário', 'Gerente', 'Superadmin']).exists():
        return redirect('dashboard:home')
    
    # Buscar histórico de edições
    historico = HistoricoEtapaFormula.objects.filter(
        formula=formula
    ).select_related('funcionario', 'etapa').order_by('timestamp_inicio')
    
    # Calcular duração de cada etapa
    etapas_com_duracao = []
    for h in historico:
        if h.timestamp_fim:
            duracao = h.timestamp_fim - h.timestamp_inicio
            horas = duracao.total_seconds() / 3600
            minutos = (duracao.total_seconds() % 3600) / 60
            tempo_str = f"{int(horas)}h {int(minutos)}min"
        else:
            # Ainda está em andamento
            tempo_str = "Em andamento..."
        
        etapas_com_duracao.append({
            'historico': h,
            'tempo': tempo_str,
        })
    
    context = {
        'formula': formula,
        'etapas_com_duracao': etapas_com_duracao,
        'total_etapas_completadas': sum(1 for e in etapas_com_duracao if e['historico'].timestamp_fim),
    }
    
    return render(request, 'dashboard/historico_etapas_formula.html', context)

@login_required
def rotas_motoboy(request):
    """Tela de gerenciamento de rotas Motoboy - pedidos aguardando envio"""
    if not request.user.groups.filter(name__in=['Funcionário', 'Gerente', 'Superadmin']).exists():
        return redirect('dashboard:home')
    
    # Buscar pedidos que estão em rota motoboy (esperando ser enviados)
    pedidos_em_rota = PedidoMestre.objects.filter(
        status='em_rota_motoboy'
    ).prefetch_related('formulas').order_by('-criado_em')
    
    context = {
        'pedidos_em_rota': pedidos_em_rota,
        'total_pedidos': pedidos_em_rota.count(),
        'rota_tipo': 'Motoboy',
    }
    
    return render(request, 'dashboard/rotas_motoboy.html', context)


@login_required
def rotas_sedex(request):
    """Tela de gerenciamento de rotas Sedex - pedidos aguardando envio"""
    if not request.user.groups.filter(name__in=['Funcionário', 'Gerente', 'Superadmin']).exists():
        return redirect('dashboard:home')
    
    # Buscar pedidos que estão em rota sedex (esperando ser enviados)
    pedidos_em_rota = PedidoMestre.objects.filter(
        status='em_rota_sedex'
    ).prefetch_related('formulas').order_by('-criado_em')
    
    context = {
        'pedidos_em_rota': pedidos_em_rota,
        'total_pedidos': pedidos_em_rota.count(),
        'rota_tipo': 'Sedex',
    }
    
    return render(request, 'dashboard/rotas_sedex.html', context)


@login_required
def finalizar_rota(request, rota_tipo):
    """Finaliza apenas os pedidos SELECIONADOS de uma rota"""
    if rota_tipo not in ['motoboy', 'sedex']:
        messages.error(request, 'Tipo de rota inválido.')
        return redirect('dashboard:home')
    
    if request.method != 'POST':
        messages.error(request, 'Método inválido.')
        return redirect('dashboard:home')
    
    # Buscar pedidos selecionados
    pedidos_ids = request.POST.getlist('pedidos_selecionados')
    if not pedidos_ids:
        messages.error(request, 'Selecione pelo menos um pedido para enviar.')
        return redirect(f'dashboard:rotas_{rota_tipo}')
    
    # Marcar como expedido apenas os selecionados
    pedidos = PedidoMestre.objects.filter(id__in=pedidos_ids)
    total_formulas = 0
    total_pedidos = 0
    
    for pedido in pedidos:
        # Marcar todas as fórmulas do pedido como expedidas
        formulas = pedido.formulas.filter(status='pronto_para_expedicao')
        for formula in formulas:
            formula.status = 'expedido'
            formula.save()
            total_formulas += 1
        
        # Marcar pedido como expedido
        pedido.status = 'expedido'
        pedido.save()
        total_pedidos += 1
        
        # Log
        LogAuditoria.objects.create(
            usuario=request.user,
            acao='finalizar_rota',
            descricao=f'Enviou pedido NRORC {pedido.nrorc} ({formulas.count()} fórmulas) via {rota_tipo.upper()}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
    
    # Criar registro de expedição (batch)
    from core.models import RegistroExpedicao
    registro_expedicao = RegistroExpedicao.objects.create(
        funcionario=request.user,
        rota_tipo=rota_tipo,
        total_pedidos=total_pedidos,
        total_formulas=total_formulas,
        observacoes=f'Expedição em {rota_tipo.upper()} com {total_pedidos} pedido(s)'
    )
    # Adicionar os pedidos ao registro
    registro_expedicao.pedidos_mestre.set(pedidos)
    
    messages.success(request, 
        f'✓ {total_pedidos} pedido(s) enviado(s) com sucesso! '
        f'({total_formulas} fórmula(s) marcadas como expedidas)')
    
    return redirect('dashboard:rotas_unificada')


@login_required
def rotas_unificada(request):
    """Dashboard unificado de rotas: disponíveis, em fila, e histórico de expedições"""
    if not request.user.groups.filter(name__in=['Funcionário', 'Gerente', 'Superadmin']).exists():
        return redirect('dashboard:home')
    
    is_funcionario = request.user.groups.filter(name='Funcionário').exists()
    
    # Se for funcionário, filtra apenas pelo que ele trabalhou
    if is_funcionario:
        # Pedidos prontos para expedição que este funcionário trabalhou
        pedidos_prontos = PedidoMestre.objects.filter(
            status__in=['pronto_para_expedicao', 'em_processamento'],
            formulas__status='pronto_para_expedicao',
            formulas__historico_etapas__funcionario=request.user
        ).distinct().prefetch_related('formulas').order_by('-criado_em')
        
        # Fila Motoboy que este funcionário trabalhou
        fila_motoboy = PedidoMestre.objects.filter(
            status='em_rota_motoboy',
            formulas__historico_etapas__funcionario=request.user
        ).distinct().prefetch_related('formulas').order_by('-criado_em')
        
        # Fila Sedex que este funcionário trabalhou
        fila_sedex = PedidoMestre.objects.filter(
            status='em_rota_sedex',
            formulas__historico_etapas__funcionario=request.user
        ).distinct().prefetch_related('formulas').order_by('-criado_em')
        
        # Histórico: Registros de expedição criados por este funcionário
        from core.models import RegistroExpedicao
        registros_expedicao = RegistroExpedicao.objects.filter(
            funcionario=request.user,
            pedidos_mestre__isnull=False
        ).distinct().prefetch_related('pedidos_mestre__formulas').order_by('-data')[:20]
        
        # Fallback: se não houver registros de expedição, mostrar pedidos expedidos (compatibilidade)
        if not registros_expedicao.exists():
            expedidos = PedidoMestre.objects.filter(
                status='expedido',
                formulas__historico_etapas__funcionario=request.user
            ).distinct().prefetch_related('formulas').order_by('-criado_em')[:10]
            total_expedidos = expedidos.count()
        else:
            expedidos = registros_expedicao
            total_expedidos = expedidos.count()
    else:
        # Gerentes/Admins veem tudo
        pedidos_prontos = PedidoMestre.objects.filter(
            status__in=['pronto_para_expedicao', 'em_processamento'],
            formulas__status='pronto_para_expedicao'
        ).distinct().prefetch_related('formulas').order_by('-criado_em')
        
        fila_motoboy = PedidoMestre.objects.filter(
            status='em_rota_motoboy'
        ).prefetch_related('formulas').order_by('-criado_em')
        
        fila_sedex = PedidoMestre.objects.filter(
            status='em_rota_sedex'
        ).prefetch_related('formulas').order_by('-criado_em')
        
        # Histórico: Registros de expedição (novo modelo unificado)
        from core.models import RegistroExpedicao
        expedidos = RegistroExpedicao.objects.filter(
            pedidos_mestre__isnull=False
        ).distinct().prefetch_related('pedidos_mestre__formulas', 'funcionario').order_by('-data')[:20]
        
        total_expedidos = RegistroExpedicao.objects.filter(pedidos_mestre__isnull=False).count()
    
    context = {
        'pedidos_prontos': pedidos_prontos,
        'fila_motoboy': fila_motoboy,
        'fila_sedex': fila_sedex,
        'expedidos': expedidos,
        'total_prontos': pedidos_prontos.count(),
        'total_motoboy': fila_motoboy.count(),
        'total_sedex': fila_sedex.count(),
        'total_expedidos': total_expedidos,
    }
    
    return render(request, 'dashboard/rotas_unificada.html', context)


@login_required
def rota_detalhes_expedido(request, pedido_id):
    """Visualizar detalhes de um pedido em rota com suas fórmulas"""
    pedido = get_object_or_404(PedidoMestre, id=pedido_id)
    
    # Verificar permissão: funcionário vê apenas seus pedidos
    if request.user.groups.filter(name='Funcionário').exists():
        if not HistoricoEtapaFormula.objects.filter(formula__pedido_mestre=pedido, funcionario=request.user).exists():
            messages.error(request, 'Você não tem permissão para ver este pedido.')
            return redirect('dashboard:rotas_unificada')
    
    # Buscar todas as fórmulas do pedido
    formulas = FormulaItem.objects.filter(
        pedido_mestre=pedido
    ).select_related('etapa_atual').prefetch_related('historico_etapas')
    
    # Determinar a rota
    if 'motoboy' in pedido.status.lower():
        rota = 'Motoboy'
    elif 'sedex' in pedido.status.lower():
        rota = 'Sedex'
    else:
        rota = 'Não definida'
    
    context = {
        'pedido': pedido,
        'formulas': formulas,
        'total_formulas': formulas.count(),
        'rota': rota,
    }
    
    return render(request, 'dashboard/rota_detalhes_expedido.html', context)


@login_required
def expedicao_detalhes(request, expedicao_id):
    """Visualizar detalhes de uma expedição (batch de pedidos)"""
    from core.models import RegistroExpedicao
    
    expedis = get_object_or_404(RegistroExpedicao, id=expedicao_id, pedidos_mestre__isnull=False)
    
    # Verificar permissão: funcionário vê apenas suas expedições
    if request.user.groups.filter(name='Funcionário').exists():
        if expedis.funcionario != request.user:
            messages.error(request, 'Você não tem permissão para ver esta expedição.')
            return redirect('dashboard:rotas_unificada')
    
    # Buscar todos os pedidos da expedição
    pedidos = expedis.pedidos_mestre.all().prefetch_related('formulas')
    
    # Mapear informações dos pedidos
    pedidos_info = []
    for pedido in pedidos:
        formulas = pedido.formulas.all()
        pedidos_info.append({
            'pedido': pedido,
            'formulas': formulas,
            'total_formulas': formulas.count(),
        })
    
    # Mapear rota
    if expedis.rota_tipo == 'motoboy':
        rota = 'Motoboy'
        rota_icon = 'bi-person-walking'
    elif expedis.rota_tipo == 'sedex':
        rota = 'Sedex'
        rota_icon = 'bi-box-seam'
    else:
        rota = 'Não definida'
        rota_icon = 'bi-truck'
    
    context = {
        'expedis': expedis,
        'pedidos_info': pedidos_info,
        'rota': rota,
        'rota_icon': rota_icon,
        'total_pedidos': pedidos.count(),
        'total_formulas': sum([p['total_formulas'] for p in pedidos_info]),
    }
    
    return render(request, 'dashboard/expedicao_detalhes.html', context)
