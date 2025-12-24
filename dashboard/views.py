from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.http import JsonResponse, HttpResponse
from decimal import Decimal
from datetime import datetime, timedelta
import csv
from core.models import (
    Pedido, Etapa, PontuacaoFuncionario, HistoricoEtapa,
    BonusFaixa, HistoricoBonusMensal, LogAuditoria, Checklist,
    ChecklistExecucao, ConfiguracaoPontuacao, RegraProducao,
    ConfiguracaoExpedicao, TipoProduto
)

# Detalhe de uma rota finalizada
@login_required
def detalhe_rota_finalizada(request, historico_id):
    historico = get_object_or_404(HistoricoEtapa.objects.select_related('pedido', 'pedido__tipo', 'funcionario'), id=historico_id)
    # Permitir acesso apenas ao próprio funcionário ou gestor
    if not (request.user == historico.funcionario or request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() or request.user.is_superuser):
        return redirect('dashboard:rotas_finalizadas')
    is_gestor = request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() or request.user.is_superuser
    context = {
        'historico': historico,
        'is_gestor': is_gestor,
    }
    return render(request, 'dashboard/detalhe_rota_finalizada.html', context)

def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    return redirect('login')

@login_required
def home(request):
    user_groups = request.user.groups.values_list('name', flat=True)
    
    if 'Funcionário' in user_groups:
        return redirect('dashboard:funcionario')
    elif 'Gerente' in user_groups:
        return redirect('dashboard:gerente')
    elif 'Superadmin' in user_groups or request.user.is_superuser:
        return redirect('dashboard:superadmin')
    
    return redirect('login')

@login_required
def dashboard_funcionario(request):
    # Verificar se o usuário é funcionário
    if not request.user.groups.filter(name='Funcionário').exists() and not request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() and not request.user.is_superuser:
        return redirect('dashboard:home')
    
    # Se for admin/gerente/superadmin, redirecionar para dashboard apropriado
    if request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() or request.user.is_superuser:
        if request.user.groups.filter(name='Superadmin').exists() or request.user.is_superuser:
            return redirect('dashboard:superadmin')
        else:
            return redirect('dashboard:gerente')
    
    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    
    pontos_mes_atual = PontuacaoFuncionario.pontos_mes_atual(request.user)
    
    faixa_bonus = BonusFaixa.objects.filter(
        ativo=True,
        faixa_min__lte=pontos_mes_atual,
        faixa_max__gte=pontos_mes_atual
    ).first()
    
    pedidos_trabalhados = Pedido.objects.filter(
        historico_etapas__funcionario=request.user
    ).distinct().count()
    
    etapas_concluidas = HistoricoEtapa.objects.filter(
        funcionario=request.user,
        timestamp_fim__isnull=False,
        timestamp_inicio__gte=primeiro_dia_mes
    ).values('etapa__nome').annotate(
        total_pontos=Sum('pontos_gerados'),
        quantidade=Count('id')
    )
    
    # Calcular evolução de pontos diária
    pontuacoes = PontuacaoFuncionario.objects.filter(
        funcionario=request.user,
        mes_referencia__gte=primeiro_dia_mes
    ).order_by('timestamp').values('timestamp', 'pontos')
    
    # Agrupar por dia e acumular pontos
    from collections import defaultdict
    from datetime import date
    pontos_por_dia = defaultdict(float)
    for p in pontuacoes:
        dia = p['timestamp'].date()
        pontos_por_dia[dia] += float(p['pontos'])
    
    # Criar lista de dias do mês com acumulado
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
    
    # Se não houver dados no mês, criar estrutura vazia
    if not dias_mes:
        dias_mes = [{'dia': hoje.strftime('%d/%m'), 'pontos': int(pontos_mes_atual)}]
    
    import json
    dias_labels = json.dumps([d['dia'] for d in dias_mes])
    dias_data = json.dumps([d['pontos'] for d in dias_mes])
    
    context = {
        'pontos_mes_atual': pontos_mes_atual,
        'faixa_bonus': faixa_bonus,
        'pedidos_trabalhados': pedidos_trabalhados,
        'etapas_concluidas': etapas_concluidas,
        'dias_labels': dias_labels,
        'dias_data': dias_data,
    }
    
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='outros',
        descricao='Acessou dashboard do funcionário',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return render(request, 'dashboard/funcionario.html', context)

@login_required
def meus_pedidos_funcionario(request):
    """Pedidos que o funcionário está trabalhando atualmente"""
    # Verificar se é funcionário
    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')
    
    pedidos_assumidos = Pedido.objects.filter(
        funcionario_na_etapa=request.user,
        status='em_fluxo'
    ).select_related('etapa_atual')
    
    context = {
        'pedidos_assumidos': pedidos_assumidos,
    }
    
    return render(request, 'dashboard/meus_pedidos.html', context)

@login_required
@login_required
def pedidos_disponiveis_funcionario(request):
    """Pedidos disponíveis para assumir com paginação"""
    # Verificar se é funcionário
    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')
    
    from django.core.paginator import Paginator
    nome = request.GET.get('nome', '').strip()
    etapa_id = request.GET.get('etapa', '')
    tipo_id = request.GET.get('tipo', '')
    id_api = request.GET.get('id_api', '').strip()
    id_pedido = request.GET.get('id_pedido', '').strip()
    id_pedido_web = request.GET.get('id_pedido_web', '').strip()

    # Buscar todos os pedidos disponíveis
    todos_pedidos = Pedido.objects.filter(
        funcionario_na_etapa__isnull=True,
        status='em_fluxo'
    ).select_related('etapa_atual', 'tipo').order_by('-data_atualizacao_api', '-hora_atualizacao_api')

    if nome:
        todos_pedidos = todos_pedidos.filter(nome__icontains=nome)
    if etapa_id:
        todos_pedidos = todos_pedidos.filter(etapa_atual_id=etapa_id)
    if tipo_id:
        todos_pedidos = todos_pedidos.filter(tipo_id=tipo_id)
    
    # Se houver busca por ID, usar OR (qualquer um dos 3 campos)
    if id_api or id_pedido or id_pedido_web:
        from django.db.models import Q
        filtro_ids = Q()
        if id_api:
            filtro_ids |= Q(id_api__icontains=id_api)
        if id_pedido:
            filtro_ids |= Q(id_pedido_api__icontains=id_pedido)
        if id_pedido_web:
            filtro_ids |= Q(id_pedido_web__icontains=id_pedido_web)
        todos_pedidos = todos_pedidos.filter(filtro_ids)

    etapas = Etapa.objects.all()
    tipos = TipoProduto.objects.all()

    # Paginação
    paginator = Paginator(todos_pedidos, 20)  # 20 pedidos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'etapas': etapas,
        'tipos': tipos,
        'filtro_nome': nome,
        'filtro_etapa': etapa_id,
        'filtro_tipo': tipo_id,
        'filtro_id_api': id_api,
        'filtro_id_pedido': id_pedido,
        'filtro_id_pedido_web': id_pedido_web,
    }

    return render(request, 'dashboard/pedidos_disponiveis.html', context)

@login_required
def assumir_pedido(request, pedido_id):
    from django.contrib import messages
    from django.urls import reverse
    
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    if pedido.funcionario_na_etapa:
        messages.error(request, 'Este pedido já foi assumido por outro funcionário.')
        return redirect('dashboard:pedidos_disponiveis')
    
    if pedido.status != 'em_fluxo':
        messages.error(request, 'Este pedido não está disponível para ser assumido.')
        return redirect('dashboard:pedidos_disponiveis')
    
    # Verificar se é etapa de Expedição
    is_expedicao = pedido.etapa_atual and pedido.etapa_atual.nome.lower() == 'expedição'
    
    # Validar LIMITE de 5 pedidos simultâneos (APENAS para etapas diferentes de Expedição)
    if not is_expedicao:
        pedidos_count = Pedido.objects.filter(
            funcionario_na_etapa=request.user,
            status='em_fluxo'
        ).count()
        
        if pedidos_count >= 5:
            return redirect(f"{reverse('dashboard:pedidos_disponiveis')}?modal=limite_pedidos")
    
    # Assumir o pedido
    pedido.funcionario_na_etapa = request.user
    
    # Para Expedição: SEMPRE ATIVO, sem pendente
    if is_expedicao:
        pedido.status_fila = 'ativo'
    else:
        # Para outras etapas: Se já tem 1 ativo, novo vem como PENDENTE
        ativo_count = Pedido.objects.filter(
            funcionario_na_etapa=request.user,
            status='em_fluxo',
            status_fila='ativo'
        ).count()
        
        if ativo_count >= 1:
            # Já tem um ativo, novo é PENDENTE
            pedido.status_fila = 'pendente'
        else:
            # Não tem nenhum ativo, novo é ATIVO
            pedido.status_fila = 'ativo'
    
    pedido.save()
    
    # Criar histórico de etapa
    HistoricoEtapa.objects.create(
        pedido=pedido,
        etapa=pedido.etapa_atual,
        funcionario=request.user
    )
    
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='assumir_etapa',
        descricao=f'Assumiu pedido #{pedido.id} na etapa {pedido.etapa_atual.nome} (status_fila: {pedido.status_fila})',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    status_msg = "ATIVO" if pedido.status_fila == 'ativo' else "PENDENTE"
    messages.success(request, f'Pedido #{pedido.id} assumido com sucesso! Status: {status_msg}')
    return redirect('dashboard:trabalhar_pedido', pedido_id=pedido.id)

@login_required
@login_required
def trabalhar_pedido(request, pedido_id):
    """Tela para trabalhar em um pedido específico"""
    from django.contrib import messages
    
    pedido = get_object_or_404(Pedido, id=pedido_id, funcionario_na_etapa=request.user)
    
    # Se estiver na etapa de Controle de Qualidade, redirecionar para o formulário
    if pedido.etapa_atual and pedido.etapa_atual.nome.lower() == 'controle de qualidade':
        return redirect('dashboard:controle_qualidade', pedido_id=pedido.id)
    
    # Se estiver na etapa de Expedição, mostrar tela de escolha (Motoboy ou Sedex)
    if pedido.etapa_atual.nome == 'Expedição':
        context = {
            'pedido': pedido,
            'etapa_expedicao': True,
        }
        return render(request, 'dashboard/trabalhar_pedido.html', context)
    
    # Buscar histórico atual
    historico = HistoricoEtapa.objects.filter(
        pedido=pedido,
        funcionario=request.user,
        timestamp_fim__isnull=True
    ).first()
    
    if not historico:
        messages.error(request, 'Erro ao carregar o pedido.')
        return redirect('dashboard:meus_pedidos')
    
    # Buscar checklists se a etapa tiver (mas NÃO para Expedição)
    checklists_execucao = []
    if pedido.etapa_atual.se_possui_checklists and pedido.etapa_atual.nome != 'Expedição':
        # Buscar todos os checklists ativos da etapa
        checklists = Checklist.objects.filter(
            etapa=pedido.etapa_atual,
            ativo=True
        ).order_by('nome')
        
        for checklist in checklists:
            exec_check, created = ChecklistExecucao.objects.get_or_create(
                historico_etapa=historico,
                checklist=checklist
            )
            checklists_execucao.append(exec_check)
    
    context = {
        'pedido': pedido,
        'historico': historico,
        'checklists_execucao': checklists_execucao,
    }
    
    return render(request, 'dashboard/trabalhar_pedido.html', context)

@login_required
def marcar_checklist(request, execucao_id):
    from django.contrib import messages
    
    execucao = get_object_or_404(ChecklistExecucao, id=execucao_id)
    
    # Verificar se o funcionário pode marcar
    if execucao.historico_etapa.funcionario != request.user:
        messages.error(request, 'Você não pode marcar este checklist.')
        return redirect('dashboard:meus_pedidos')
    
    # Alternar marcação (funciona com GET ou POST)
    execucao.marcado = not execucao.marcado
    if execucao.marcado:
        execucao.marcado_em = timezone.now()
        execucao.pontos_gerados = execucao.checklist.pontos_do_check
    else:
        execucao.marcado_em = None
        execucao.pontos_gerados = Decimal('0')
    
    execucao.save()
    
    return redirect('dashboard:trabalhar_pedido', pedido_id=execucao.historico_etapa.pedido.id)

@login_required
def toggle_status_fila(request, pedido_id):
    """Alterna entre status ATIVO e PENDENTE de um pedido"""
    from django.contrib import messages
    
    pedido = get_object_or_404(Pedido, id=pedido_id, funcionario_na_etapa=request.user)
    
    # Validar que pedido está em fluxo
    if pedido.status != 'em_fluxo':
        messages.error(request, 'Você só pode alternar status de pedidos em fluxo.')
        return redirect('dashboard:trabalhar_pedido', pedido_id=pedido_id)
    
    if pedido.status_fila == 'ativo':
        # Mudar para PENDENTE
        # Verificar se está em sessão de expedição
        pedidos_motoboy = request.session.get('pedidos_motoboy', [])
        pedidos_sedex = request.session.get('pedidos_sedex', [])
        em_sessao_expedicao = pedido.id in pedidos_motoboy or pedido.id in pedidos_sedex
        
        success, msg = pedido.marcar_como_pendente(em_sessao_expedicao=em_sessao_expedicao)
        if success:
            messages.success(request, f'Pedido #{pedido.id_api} movido para PENDENTE. Você pode trabalhar em outro pedido.')
        else:
            messages.error(request, msg)
    else:
        # IMPORTANTE: Antes de ativar, garantir que não há outro ativo
        # Colocar todos os outros como PENDENTE (EXCETO os de Expedição que sempre permanecem ATIVO)
        etapa_expedicao = Etapa.objects.filter(nome='Expedição').first()
        
        Pedido.objects.filter(
            funcionario_na_etapa=request.user,
            status='em_fluxo',
            status_fila='ativo'
        ).exclude(
            id=pedido.id
        ).exclude(
            etapa_atual=etapa_expedicao
        ).update(status_fila='pendente')
        
        # Agora marcar este como ATIVO
        pedido.status_fila = 'ativo'
        pedido.save()
        
        messages.success(request, f'Pedido #{pedido.id_api} ATIVADO. Os outros pedidos foram colocados em PENDENTE.')
    
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='toggle_status_fila',
        descricao=f'Alterou status_fila do pedido #{pedido.id} para {pedido.status_fila}',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return redirect('dashboard:trabalhar_pedido', pedido_id=pedido_id)

@login_required
def concluir_etapa(request, pedido_id):
    from django.contrib import messages
    from core.models import ConfiguracaoPontuacao, PontuacaoPorAtividade
    
    # Buscar pedido sem restrição de funcionário primeiro
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Se estiver na etapa de Controle de Qualidade, redirecionar para o formulário
    if pedido.etapa_atual and pedido.etapa_atual.nome.lower() == 'controle de qualidade':
        return redirect('dashboard:controle_qualidade', pedido_id=pedido.id)
    
    if request.method == 'POST':
        # Verificar se o usuário é o funcionário na etapa
        if pedido.funcionario_na_etapa != request.user:
            messages.error(request, 'Você não é o responsável por este pedido.')
            return redirect('dashboard:meus_pedidos')
        
        # Validar: pedido PENDENTE não pode ser concluído
        if pedido.status_fila == 'pendente':
            messages.error(request, 'Você não pode concluir esta etapa enquanto o pedido está em status PENDENTE. Clique em "Ativar Pedido" primeiro.')
            return redirect('dashboard:trabalhar_pedido', pedido_id=pedido_id)
        
        # Buscar histórico atual
        historico = HistoricoEtapa.objects.filter(
            pedido=pedido,
            funcionario=request.user,
            timestamp_fim__isnull=True
        ).first()
        
        if not historico:
            messages.error(request, 'Histórico de etapa não encontrado.')
            return redirect('dashboard:meus_pedidos')
        
        # Calcular pontos
        pontos_totais = Decimal('0')
        etapa = pedido.etapa_atual
        
        if etapa and etapa.se_gera_pontos:
            # Tentar calcular pontos por atividade se o pedido tem tipo definido
            if pedido.tipo:
                pontos_totais = PontuacaoPorAtividade.calcular_pontos(
                    etapa=etapa,
                    atividade='encapsulacao',  # Default para produção
                    tipo_produto=pedido.tipo,
                    quantidade=pedido.quantidade
                )
            
            # Se não conseguiu calcular por atividade, tentar por checklist
            if pontos_totais == 0 and etapa.se_possui_checklists:
                config = ConfiguracaoPontuacao.get_versao_ativa(etapa)
                if config:
                    pontos_totais = config.pontos_fixos
                    checklists_marcados = ChecklistExecucao.objects.filter(
                        historico_etapa=historico,
                        marcado=True
                    ).count()
                    pontos_totais += config.pontos_por_check * checklists_marcados
            
            # Se ainda não tiver pontos, usar pontuação fixa
            elif pontos_totais == 0:
                config = ConfiguracaoPontuacao.get_versao_ativa(etapa)
                if config:
                    pontos_totais = config.pontos_fixos
            
            # Adicionar pontos fixos da etapa (sempre, além de outros pontos)
            pontos_totais += Decimal(str(etapa.pontos_fixos_etapa))
        
        # Finalizar histórico
        historico.timestamp_fim = timezone.now()
        historico.pontos_gerados = pontos_totais
        historico.observacoes = request.POST.get('observacoes', '')
        historico.save()
        
        # Registrar pontos
        if pontos_totais > 0:
            PontuacaoFuncionario.objects.create(
                funcionario=request.user,
                pedido=pedido,
                etapa=etapa,
                pontos=pontos_totais,
                origem='producao' if etapa and etapa.nome.lower() == 'produção' else 'etapa',
                mes_referencia=timezone.now().date()
            )
        
        # Avançar pedido para próxima etapa
        pedido.avancar_etapa()
        
        LogAuditoria.objects.create(
            usuario=request.user,
            acao='concluir_etapa',
            descricao=f'Concluiu etapa {etapa.nome if etapa else "desconhecida"} do pedido #{pedido.id}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, f'Etapa concluída!')
        return redirect('dashboard:meus_pedidos')
    
    return redirect('dashboard:meus_pedidos')

@login_required
def selecionar_rota_expedicao(request, pedido_id, tipo_rota):
    """Registra qual rota de expedição foi selecionada (motoboy ou sedex)"""
    from django.contrib import messages
    
    if tipo_rota not in ['motoboy', 'sedex']:
        messages.error(request, 'Tipo de rota inválido.')
        return redirect('dashboard:trabalhar_pedido', pedido_id=pedido_id)
    
    pedido = get_object_or_404(Pedido, id=pedido_id, funcionario_na_etapa=request.user)
    
    # Se o pedido já estava vinculado a outra rota, remove da sessão anterior
    rota_anterior = pedido.tipo_expedicao
    if rota_anterior and rota_anterior != tipo_rota:
        # Remove da sessão da rota anterior
        if rota_anterior == 'motoboy':
            pedidos_motoboy = request.session.get('pedidos_motoboy', [])
            if pedido_id in pedidos_motoboy:
                pedidos_motoboy.remove(pedido_id)
                request.session['pedidos_motoboy'] = pedidos_motoboy
        elif rota_anterior == 'sedex':
            pedidos_sedex = request.session.get('pedidos_sedex', [])
            if pedido_id in pedidos_sedex:
                pedidos_sedex.remove(pedido_id)
                request.session['pedidos_sedex'] = pedidos_sedex
    
    # Registra qual rota foi selecionada
    pedido.tipo_expedicao = tipo_rota
    pedido.save()
    
    # Redireciona para a página de expedição correta
    if tipo_rota == 'motoboy':
        return redirect('dashboard:expedicao_motoboy')
    else:
        return redirect('dashboard:expedicao_sedex')

@login_required
def expedicao_motoboy(request):
    """Tela para criar rotas de motoboy selecionando pedidos"""
    # Verificar se é funcionário
    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')
    
    from django.contrib import messages
    
    # Buscar configuração do Motoboy definida pelo Gestor
    config_motoboy = ConfiguracaoExpedicao.objects.filter(tipo_expedicao='motoboy', ativo=True).first()
    
    if not config_motoboy:
        messages.error(request, 'Configuração de Motoboy não encontrada. Contate o administrador.')
        return redirect('dashboard:meus_pedidos')
    
    # Buscar APENAS os pedidos que o funcionário assumiu na etapa de Expedição
    etapa_expedicao = Etapa.objects.get(nome='Expedição')
    
    # Pedidos já selecionados nesta sessão
    pedidos_selecionados_ids = request.session.get('pedidos_motoboy', [])
    
    # Pedidos disponíveis: apenas os com tipo_expedicao='motoboy' (ou sem tipo_expedicao se nunca foram selecionados)
    # Excluindo os já selecionados nesta sessão
    pedidos_disponiveis = Pedido.objects.filter(
        etapa_atual=etapa_expedicao,
        funcionario_na_etapa=request.user,
        status='em_fluxo',
        tipo_expedicao__in=['motoboy', None]  # Apenas motoboy ou sem seleção
    ).exclude(id__in=pedidos_selecionados_ids).select_related('tipo').order_by('-criado_em')
    
    pedidos_selecionados = Pedido.objects.filter(id__in=pedidos_selecionados_ids)
    
    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'adicionar' or acao == 'adicionar_individual':
            # Adicionar pedido à rota (individual ou via checkbox)
            pedido_id = int(request.POST.get('pedido_id'))
            pedido = get_object_or_404(Pedido, id=pedido_id, etapa_atual=etapa_expedicao)
            
            if pedido_id not in pedidos_selecionados_ids:
                pedidos_selecionados_ids.append(pedido_id)
                request.session['pedidos_motoboy'] = pedidos_selecionados_ids
                messages.success(request, f'Pedido #{pedido.id} adicionado à rota')
            
            return redirect('dashboard:expedicao_motoboy')
        
        elif acao == 'adicionar_selecionados':
            # Adicionar múltiplos pedidos em lote
            pedidos_ids = request.POST.getlist('pedidos_selecionados')
            if pedidos_ids:
                for pedido_id in pedidos_ids:
                    pedido_id = int(pedido_id)
                    if pedido_id not in pedidos_selecionados_ids:
                        pedido = get_object_or_404(Pedido, id=pedido_id, etapa_atual=etapa_expedicao)
                        pedidos_selecionados_ids.append(pedido_id)
                request.session['pedidos_motoboy'] = pedidos_selecionados_ids
                messages.success(request, f'{len(pedidos_ids)} pedido(s) adicionado(s) à rota')
            else:
                messages.warning(request, 'Nenhum pedido foi selecionado')
            
            return redirect('dashboard:expedicao_motoboy')
        
        elif acao == 'remover':
            # Remover pedido da rota - apenas da sessão, volta para pedidos disponíveis
            pedido_id = int(request.POST.get('pedido_id'))
            try:
                pedido = Pedido.objects.get(id=pedido_id)
                pedido_nome = f"#{pedido.id_api}"
                
                # Remover APENAS da sessão (não limpa tipo_expedicao do banco)
                if pedido_id in pedidos_selecionados_ids:
                    pedidos_selecionados_ids.remove(pedido_id)
                    request.session['pedidos_motoboy'] = pedidos_selecionados_ids
                    request.session.modified = True
                
                messages.success(request, f'Pedido {pedido_nome} devolvido aos pedidos disponíveis!')
            except Pedido.DoesNotExist:
                messages.error(request, 'Pedido não encontrado.')
            
            # Manter na tela
            return redirect('dashboard:expedicao_motoboy')
        
        elif acao == 'remover_expedicao':
            # Remover expedição - manter na tela
            pedido_id = int(request.POST.get('pedido_id'))
            try:
                pedido = Pedido.objects.get(id=pedido_id)
                pedido_nome = f"#{pedido.id_api}"
                
                # Limpar tipo_expedicao do banco
                if pedido.tipo_expedicao:
                    pedido.tipo_expedicao = None
                    pedido.save()
                
                # Remover da sessão
                if pedido_id in pedidos_selecionados_ids:
                    pedidos_selecionados_ids.remove(pedido_id)
                    request.session['pedidos_motoboy'] = pedidos_selecionados_ids
                    request.session.modified = True
                
                messages.success(request, f'Pedido {pedido_nome} removido! Agora você pode selecionar outra rota.')
            except Pedido.DoesNotExist:
                messages.error(request, 'Pedido não encontrado.')
            
            # Manter na tela
            return redirect('dashboard:expedicao_motoboy')
        
        elif acao == 'remover_expedicao_lote':
            # Remover expedição para múltiplos pedidos selecionados - manter na tela
            pedidos_ids = request.POST.getlist('pedidos_selecionados')
            if pedidos_ids:
                try:
                    for pedido_id in pedidos_ids:
                        pedido_id = int(pedido_id)
                        pedido = Pedido.objects.get(id=pedido_id)
                        
                        # Limpar tipo_expedicao do banco
                        if pedido.tipo_expedicao:
                            pedido.tipo_expedicao = None
                            pedido.save()
                        
                        # Remover da sessão
                        if pedido_id in pedidos_selecionados_ids:
                            pedidos_selecionados_ids.remove(pedido_id)
                    
                    request.session['pedidos_motoboy'] = pedidos_selecionados_ids
                    request.session.modified = True
                    messages.success(request, f'{len(pedidos_ids)} pedido(s) removido(s) da expedição!')
                except Exception as e:
                    messages.error(request, f'Erro ao remover expedição: {str(e)}')
            else:
                messages.warning(request, 'Nenhum pedido foi selecionado')
            
            # Manter na tela
            return redirect('dashboard:expedicao_motoboy')
        
        elif acao == 'cancelar':
            # Cancelar rota - limpar sessão e permanecer na mesma página
            if pedidos_selecionados_ids:
                try:
                    # Limpar o tipo_expedicao do banco de dados para todos os pedidos selecionados
                    Pedido.objects.filter(id__in=pedidos_selecionados_ids).update(tipo_expedicao=None)
                    request.session['pedidos_motoboy'] = []
                    request.session.modified = True
                    messages.success(request, 'Expedição removida. Os pedidos retornaram aos disponíveis.')
                except Exception as e:
                    messages.error(request, f'Erro ao cancelar: {str(e)}')
            return redirect('dashboard:expedicao_motoboy')
        
        elif acao == 'finalizar':
            # Finalizar rota e atribuir pontos conforme configuração do gestor
            if not pedidos_selecionados_ids:
                messages.error(request, 'Selecione pelo menos um pedido para criar uma rota')
                return redirect('dashboard:expedicao_motoboy')
            
            # Processar cada pedido selecionado
            total_pedidos = 0
            try:
                checklist_motoboy = Checklist.objects.get(
                    etapa=etapa_expedicao,
                    nome='ROTA MOTOBOY'
                )
            except Checklist.DoesNotExist:
                messages.error(request, 'Checklist "ROTA MOTOBOY" não configurado')
                return redirect('dashboard:expedicao_motoboy')
            
            for pedido_id in pedidos_selecionados_ids:
                try:
                    pedido = Pedido.objects.get(id=pedido_id)
                    
                    # Assumir o pedido se ainda não foi assumido
                    if not pedido.funcionario_na_etapa:
                        pedido.funcionario_na_etapa = request.user
                        pedido.save()
                    
                    # Criar ou buscar histórico existente
                    historico, created = HistoricoEtapa.objects.get_or_create(
                        pedido=pedido,
                        etapa=etapa_expedicao,
                        funcionario=request.user,
                        timestamp_fim__isnull=True,
                        defaults={'timestamp_inicio': timezone.now()}
                    )
                    
                    # Marcar checklist ROTA MOTOBOY
                    exec_check, _ = ChecklistExecucao.objects.get_or_create(
                        historico_etapa=historico,
                        checklist=checklist_motoboy
                    )
                    exec_check.marcado = True
                    exec_check.marcado_em = timezone.now()
                    exec_check.pontos_gerados = checklist_motoboy.pontos_do_check
                    exec_check.save()
                    
                    # Finalizar histórico com pontos conforme configuração
                    pontos_rota = config_motoboy.pontos_por_rota_motoboy
                    historico.timestamp_fim = timezone.now()
                    historico.pontos_gerados = pontos_rota + Decimal(str(etapa_expedicao.pontos_fixos_etapa))
                    historico.save()
                    
                    # Registrar pontuação
                    pontos_total_com_etapa = pontos_rota + Decimal(str(etapa_expedicao.pontos_fixos_etapa))
                    PontuacaoFuncionario.objects.create(
                        funcionario=request.user,
                        pedido=pedido,
                        etapa=etapa_expedicao,
                        pontos=pontos_total_com_etapa,
                        origem='expedicao',
                        mes_referencia=timezone.now().date()
                    )
                    
                    # Avançar pedido para próxima etapa
                    pedido.avancar_etapa()
                    total_pedidos += 1
                except Pedido.DoesNotExist:
                    messages.warning(request, f'Pedido #{pedido_id} não encontrado')
                    continue
            
            # Limpar sessão
            request.session['pedidos_motoboy'] = []
            
            messages.success(request, f'Rota finalizada! {total_pedidos} pedido(s) processado(s)')
            return redirect('dashboard:meus_pedidos')
    
    context = {
        'pedidos_disponiveis': pedidos_disponiveis,
        'pedidos_selecionados': pedidos_selecionados,
        'config_motoboy': config_motoboy,
        'total_pontos': len(pedidos_selecionados_ids) * config_motoboy.pontos_por_rota_motoboy,
    }
    
    return render(request, 'dashboard/expedicao_motoboy.html', context)

@login_required
def expedicao_sedex(request):
    """Tela para criar rotas de sedex - pontuação conforme configuração do Gestor"""
    # Verificar se é funcionário
    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')
    
    from django.contrib import messages
    
    # Buscar configuração do Sedex definida pelo Gestor
    config_sedex = ConfiguracaoExpedicao.objects.filter(tipo_expedicao='sedex', ativo=True).first()
    
    if not config_sedex:
        messages.error(request, 'Configuração de Sedex não encontrada. Contate o administrador.')
        return redirect('dashboard:meus_pedidos')
    
    # Buscar APENAS os pedidos que o funcionário assumiu na etapa de Expedição
    etapa_expedicao = Etapa.objects.get(nome='Expedição')
    
    # Pedidos já selecionados para sedex nesta sessão
    pedidos_selecionados_ids = request.session.get('pedidos_sedex', [])
    
    # Pedidos disponíveis: apenas os com tipo_expedicao='sedex' (ou sem tipo_expedicao se nunca foram selecionados)
    # Excluindo os já selecionados nesta sessão
    pedidos_disponiveis = Pedido.objects.filter(
        etapa_atual=etapa_expedicao,
        funcionario_na_etapa=request.user,
        status='em_fluxo',
        tipo_expedicao__in=['sedex', None]  # Apenas sedex ou sem seleção
    ).exclude(id__in=pedidos_selecionados_ids).select_related('tipo').order_by('-criado_em')
    
    pedidos_selecionados = Pedido.objects.filter(id__in=pedidos_selecionados_ids)
    
    # Verificar se já processou sedex hoje (para contagem por dia)
    hoje = timezone.now().date()
    sedex_processado_hoje = False
    if config_sedex.tipo_pontuacao_sedex == 'por_dia':
        sedex_processado_hoje = ChecklistExecucao.objects.filter(
            checklist__nome='SEDEX',
            checklist__etapa=etapa_expedicao,
            historico_etapa__funcionario=request.user,
            marcado_em__date=hoje
        ).exists()
    
    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'adicionar' or acao == 'adicionar_individual':
            # Adicionar pedido ao sedex (individual ou via checkbox)
            pedido_id = int(request.POST.get('pedido_id'))
            pedido = get_object_or_404(Pedido, id=pedido_id, etapa_atual=etapa_expedicao, funcionario_na_etapa=request.user)
            
            if pedido_id not in pedidos_selecionados_ids:
                pedidos_selecionados_ids.append(pedido_id)
                request.session['pedidos_sedex'] = pedidos_selecionados_ids
                messages.success(request, f'Pedido #{pedido.id} adicionado ao sedex')
            
            return redirect('dashboard:expedicao_sedex')
        
        elif acao == 'adicionar_selecionados':
            # Adicionar múltiplos pedidos em lote
            pedidos_ids = request.POST.getlist('pedidos_selecionados')
            if pedidos_ids:
                for pedido_id in pedidos_ids:
                    pedido_id = int(pedido_id)
                    if pedido_id not in pedidos_selecionados_ids:
                        pedido = get_object_or_404(Pedido, id=pedido_id, etapa_atual=etapa_expedicao, funcionario_na_etapa=request.user)
                        pedidos_selecionados_ids.append(pedido_id)
                request.session['pedidos_sedex'] = pedidos_selecionados_ids
                messages.success(request, f'{len(pedidos_ids)} pedido(s) adicionado(s) ao sedex')
            else:
                messages.warning(request, 'Nenhum pedido foi selecionado')
            
            return redirect('dashboard:expedicao_sedex')
        
        elif acao == 'remover':
            # Remover pedido da rota - apenas da sessão, volta para pedidos disponíveis
            pedido_id = int(request.POST.get('pedido_id'))
            try:
                pedido = Pedido.objects.get(id=pedido_id)
                pedido_nome = f"#{pedido.id_api}"
                
                # Remover APENAS da sessão (não limpa tipo_expedicao do banco)
                if pedido_id in pedidos_selecionados_ids:
                    pedidos_selecionados_ids.remove(pedido_id)
                    request.session['pedidos_sedex'] = pedidos_selecionados_ids
                    request.session.modified = True
                
                messages.success(request, f'Pedido {pedido_nome} devolvido aos pedidos disponíveis!')
            except Pedido.DoesNotExist:
                messages.error(request, 'Pedido não encontrado.')
            
            # Manter na tela
            return redirect('dashboard:expedicao_sedex')
        
        elif acao == 'remover_expedicao':
            # Remover expedição - manter na tela
            pedido_id = int(request.POST.get('pedido_id'))
            try:
                pedido = Pedido.objects.get(id=pedido_id)
                pedido_nome = f"#{pedido.id_api}"
                
                # Limpar tipo_expedicao do banco
                if pedido.tipo_expedicao:
                    pedido.tipo_expedicao = None
                    pedido.save()
                
                # Remover da sessão
                if pedido_id in pedidos_selecionados_ids:
                    pedidos_selecionados_ids.remove(pedido_id)
                    request.session['pedidos_sedex'] = pedidos_selecionados_ids
                    request.session.modified = True
                
                messages.success(request, f'Pedido {pedido_nome} removido! Agora você pode selecionar outra rota.')
            except Pedido.DoesNotExist:
                messages.error(request, 'Pedido não encontrado.')
            
            # Manter na tela
            return redirect('dashboard:expedicao_sedex')
        
        elif acao == 'remover_expedicao_lote':
            # Remover expedição para múltiplos pedidos selecionados - manter na tela
            pedidos_ids = request.POST.getlist('pedidos_selecionados')
            if pedidos_ids:
                try:
                    for pedido_id in pedidos_ids:
                        pedido_id = int(pedido_id)
                        pedido = Pedido.objects.get(id=pedido_id)
                        
                        # Limpar tipo_expedicao do banco
                        if pedido.tipo_expedicao:
                            pedido.tipo_expedicao = None
                            pedido.save()
                        
                        # Remover da sessão
                        if pedido_id in pedidos_selecionados_ids:
                            pedidos_selecionados_ids.remove(pedido_id)
                    
                    request.session['pedidos_sedex'] = pedidos_selecionados_ids
                    request.session.modified = True
                    messages.success(request, f'{len(pedidos_ids)} pedido(s) removido(s) da expedição!')
                except Exception as e:
                    messages.error(request, f'Erro ao remover expedição: {str(e)}')
            else:
                messages.warning(request, 'Nenhum pedido foi selecionado')
            
            # Manter na tela
            return redirect('dashboard:expedicao_sedex')
        
        elif acao == 'cancelar':
            # Cancelar sedex - limpar sessão e permanecer na mesma página
            if pedidos_selecionados_ids:
                try:
                    # Limpar o tipo_expedicao do banco de dados para todos os pedidos selecionados
                    Pedido.objects.filter(id__in=pedidos_selecionados_ids).update(tipo_expedicao=None)
                    request.session['pedidos_sedex'] = []
                    request.session.modified = True
                    messages.success(request, 'Expedição removida. Os pedidos retornaram aos disponíveis.')
                except Exception as e:
                    messages.error(request, f'Erro ao cancelar: {str(e)}')
            return redirect('dashboard:expedicao_sedex')
        
        elif acao == 'finalizar':
            # Finalizar sedex conforme configuração do Gestor
            if not pedidos_selecionados_ids:
                messages.error(request, 'Selecione pelo menos um pedido para criar um envio sedex')
                return redirect('dashboard:expedicao_sedex')
            
            # Processar cada pedido selecionado
            total_pedidos = 0
            pontos_totais = Decimal('0')
            
            try:
                checklist_sedex = Checklist.objects.get(
                    etapa=etapa_expedicao,
                    nome='SEDEX'
                )
            except Checklist.DoesNotExist:
                messages.error(request, 'Checklist "SEDEX" não configurado')
                return redirect('dashboard:expedicao_sedex')
            
            for pedido_id in pedidos_selecionados_ids:
                try:
                    pedido = Pedido.objects.get(id=pedido_id)
                    
                    # Assumir o pedido se ainda não foi assumido
                    if not pedido.funcionario_na_etapa:
                        pedido.funcionario_na_etapa = request.user
                        pedido.save()
                    
                    # Criar ou buscar histórico existente
                    historico, created = HistoricoEtapa.objects.get_or_create(
                        pedido=pedido,
                        etapa=etapa_expedicao,
                        funcionario=request.user,
                        timestamp_fim__isnull=True,
                        defaults={'timestamp_inicio': timezone.now()}
                    )
                    
                    # Marcar checklist SEDEX
                    exec_check, _ = ChecklistExecucao.objects.get_or_create(
                        historico_etapa=historico,
                        checklist=checklist_sedex
                    )
                    
                    # Calcular pontos conforme tipo de contagem do Gestor
                    if config_sedex.tipo_pontuacao_sedex == 'por_dia':
                        # Por dia: marca apenas uma vez
                        if not exec_check.marcado:
                            exec_check.marcado = True
                            exec_check.marcado_em = timezone.now()
                            exec_check.pontos_gerados = checklist_sedex.pontos_do_check
                            pontos_rota = config_sedex.pontos_sedex
                        else:
                            pontos_rota = Decimal('0')  # Já foi marcado hoje
                    else:
                        # Por envio/rota: marca cada rota
                        exec_check.marcado = True
                        exec_check.marcado_em = timezone.now()
                        exec_check.pontos_gerados = checklist_sedex.pontos_do_check
                        pontos_rota = config_sedex.pontos_sedex
                    
                    exec_check.save()
                    
                    # Finalizar histórico com pontos
                    historico.timestamp_fim = timezone.now()
                    historico.pontos_gerados = pontos_rota + Decimal(str(etapa_expedicao.pontos_fixos_etapa))
                    historico.save()
                    
                    # Registrar pontuação
                    pontos_total_com_etapa = pontos_rota + Decimal(str(etapa_expedicao.pontos_fixos_etapa))
                    if pontos_total_com_etapa > 0:
                        PontuacaoFuncionario.objects.create(
                            funcionario=request.user,
                            pedido=pedido,
                            etapa=etapa_expedicao,
                            pontos=pontos_total_com_etapa,
                            origem='expedicao',
                            mes_referencia=timezone.now().date()
                        )
                        pontos_totais += pontos_total_com_etapa
                    
                    # Avançar pedido para próxima etapa
                    pedido.avancar_etapa()
                    total_pedidos += 1
                except Pedido.DoesNotExist:
                    messages.warning(request, f'Pedido #{pedido_id} não encontrado')
                    continue
            
            # Limpar sessão
            request.session['pedidos_sedex'] = []
            
            modo_texto = 'por dia' if config_sedex.tipo_pontuacao_sedex == 'por_dia' else 'por envio'
            messages.success(request, f'Sedex finalizado ({modo_texto})! {total_pedidos} pedido(s) processado(s)')
            return redirect('dashboard:meus_pedidos')
    
    # Calcular pontos a ganhar conforme configuração
    if config_sedex.tipo_pontuacao_sedex == 'por_dia':
        total_pontos = config_sedex.pontos_sedex if not sedex_processado_hoje else 0
    else:
        total_pontos = len(pedidos_selecionados_ids) * config_sedex.pontos_sedex
    
    context = {
        'pedidos_disponiveis': pedidos_disponiveis,
        'pedidos_selecionados': pedidos_selecionados,
        'config_sedex': config_sedex,
        'sedex_processado_hoje': sedex_processado_hoje,
        'total_pontos': total_pontos,
    }
    
    return render(request, 'dashboard/expedicao_sedex.html', context)

    
    context = {
        'config': config,
        'registros_hoje': registros_hoje,
        'pedidos_disponiveis': pedidos_disponiveis,
    }
    
    return render(request, 'dashboard/expedicao_sedex.html', context)

# Rotas Finalizadas - Funcionário (apenas as dele)
@login_required
def rotas_finalizadas_funcionario(request):
    # Verificar se é funcionário
    if not request.user.groups.filter(name='Funcionário').exists():
        return redirect('dashboard:home')
    
    etapa_expedicao = Etapa.objects.get(nome='Expedição')
    rotas_finalizadas = (
        HistoricoEtapa.objects.filter(
            funcionario=request.user,
            etapa=etapa_expedicao,
            timestamp_fim__isnull=False
        )
        .select_related('pedido', 'pedido__tipo', 'funcionario')
        .order_by('-timestamp_fim')
    )
    context = {
        'rotas_finalizadas': rotas_finalizadas,
        'is_gestor': False,
    }
    return render(request, 'dashboard/rotas_finalizadas.html', context)


# Rotas Finalizadas - Gestor (todas)
@login_required
def rotas_finalizadas_gerente(request):
    if not request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() and not request.user.is_superuser:
        return redirect('dashboard:rotas_finalizadas')
    etapa_expedicao = Etapa.objects.get(nome='Expedição')
    funcionario_nome = request.GET.get('funcionario', '').strip()
    rotas_finalizadas = HistoricoEtapa.objects.filter(
        etapa=etapa_expedicao,
        timestamp_fim__isnull=False
    )
    if funcionario_nome:
        # Filtrar por nome do funcionário - dividir em partes como em controle_qualidade
        partes_nome = funcionario_nome.split()
        from django.db.models import Q
        query = Q()
        for parte in partes_nome:
            query |= (
                Q(funcionario__first_name__icontains=parte) | 
                Q(funcionario__last_name__icontains=parte) |
                Q(funcionario__username__icontains=parte)
            )
        rotas_finalizadas = rotas_finalizadas.filter(query)
    rotas_finalizadas = rotas_finalizadas.select_related('pedido', 'pedido__tipo', 'funcionario').order_by('-timestamp_fim')
    
    # Obter lista de funcionários para autocomplete
    funcionarios_lista = HistoricoEtapa.objects.filter(
        etapa=etapa_expedicao,
        timestamp_fim__isnull=False
    ).values_list(
        'funcionario__first_name', 'funcionario__last_name', 'funcionario__username'
    ).distinct().order_by('funcionario__first_name')
    
    funcionarios_json = []
    for first_name, last_name, username in funcionarios_lista:
        nome_completo = f"{first_name} {last_name}".strip()
        if not nome_completo:
            nome_completo = username
        funcionarios_json.append({'nome': nome_completo})
    
    import json
    funcionarios_json = json.dumps(funcionarios_json)
    
    context = {
        'rotas_finalizadas': rotas_finalizadas,
        'filtro_funcionario': funcionario_nome,
        'funcionarios_json': funcionarios_json,
        'is_gestor': True,
    }
    return render(request, 'dashboard/rotas_finalizadas.html', context)

@login_required
@login_required
def historico_etapas_funcionario(request):
    """Histórico de pedidos agrupado com última etapa completada"""
    from django.core.paginator import Paginator
    
    usuario = request.user
    
    # Buscar todos os históricos de etapas do funcionário
    todos_historicos = HistoricoEtapa.objects.filter(
        funcionario=usuario,
        timestamp_fim__isnull=False
    ).select_related('pedido', 'etapa').order_by('-timestamp_fim')
    
    # Agrupar por pedido e pegar apenas a última etapa de cada um
    pedidos_dict = {}
    for historico in todos_historicos:
        if historico.pedido.id not in pedidos_dict:
            pedidos_dict[historico.pedido.id] = historico
    
    # Converter para lista ordenada
    historicos_por_pedido = list(pedidos_dict.values())
    historicos_por_pedido.sort(key=lambda x: x.timestamp_fim, reverse=True)
    
    # Resumo: agrupar por pedido com contagem de etapas e pontos totais
    resumo_pedidos = {}
    for historico in todos_historicos:
        if historico.pedido.id not in resumo_pedidos:
            resumo_pedidos[historico.pedido.id] = {
                'pedido': historico.pedido,
                'etapas_count': 0,
                'pontos_total': 0,
                'etapas': []
            }
        resumo_pedidos[historico.pedido.id]['etapas_count'] += 1
        resumo_pedidos[historico.pedido.id]['pontos_total'] += historico.pontos_gerados or 0
        resumo_pedidos[historico.pedido.id]['etapas'].append(historico.etapa.nome)
    
    resumo_etapas = list(resumo_pedidos.values())
    resumo_etapas.sort(key=lambda x: x['pontos_total'], reverse=True)
    
    # Paginar o resumo
    paginator = Paginator(resumo_etapas, 10)  # 10 itens por página
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'historicos': historicos_por_pedido,
        'resumo_etapas': page_obj.object_list,
        'page_obj': page_obj,
    }
    
    return render(request, 'dashboard/historico_etapas_funcionario.html', context)

@login_required
def pedidos_concluidos(request):
    """Tela de pedidos concluídos do sistema (visível para gerente/admin e funcionários)"""
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    # Pedidos com status concluído
    pedidos_concluidos = Pedido.objects.filter(
        status='concluido'
    ).select_related('tipo').order_by('-concluido_em')
    
    # Se for funcionário, mostrar apenas seus
    if request.user.groups.filter(name='Funcionário').exists():
        pedidos_concluidos = pedidos_concluidos.filter(
            historico_etapas__funcionario=request.user
        ).distinct()
    
    # Processar filtros
    filtros = {
        'nrorc': '',
        'nome': '',
        'tipo': '',
        'data_inicio': '',
        'data_fim': '',
    }
    
    # Filtro por NRORC
    nrorc_filtro = request.GET.get('nrorc', '').strip()
    if nrorc_filtro:
        pedidos_concluidos = pedidos_concluidos.filter(nrorc__icontains=nrorc_filtro)
        filtros['nrorc'] = nrorc_filtro
    
    # Filtro por nome
    nome_filtro = request.GET.get('nome', '').strip()
    if nome_filtro:
        pedidos_concluidos = pedidos_concluidos.filter(nome__icontains=nome_filtro)
        filtros['nome'] = nome_filtro
    
    # Filtro por tipo
    tipo_filtro = request.GET.get('tipo', '').strip()
    if tipo_filtro:
        pedidos_concluidos = pedidos_concluidos.filter(tipo__tipo__icontains=tipo_filtro)
        filtros['tipo'] = tipo_filtro
    
    # Filtro por data início
    data_inicio_filtro = request.GET.get('data_inicio', '').strip()
    if data_inicio_filtro:
        from datetime import datetime as dt
        try:
            data_inicio = dt.strptime(data_inicio_filtro, '%Y-%m-%d').date()
            pedidos_concluidos = pedidos_concluidos.filter(concluido_em__date__gte=data_inicio)
            filtros['data_inicio'] = data_inicio_filtro
        except:
            pass
    
    # Filtro por data fim
    data_fim_filtro = request.GET.get('data_fim', '').strip()
    if data_fim_filtro:
        from datetime import datetime as dt
        try:
            data_fim = dt.strptime(data_fim_filtro, '%Y-%m-%d').date()
            pedidos_concluidos = pedidos_concluidos.filter(concluido_em__date__lte=data_fim)
            filtros['data_fim'] = data_fim_filtro
        except:
            pass
    
    # Paginação
    paginator = Paginator(pedidos_concluidos, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Obter lista de tipos para dropdown
    tipos_disponiveis = TipoProduto.objects.filter(ativo=True).order_by('tipo')
    
    context = {
        'page_obj': page_obj,
        'pedidos_concluidos': page_obj,
        'filtros': filtros,
        'tipos_disponiveis': tipos_disponiveis,
    }
    
    return render(request, 'dashboard/pedidos_concluidos.html', context)

@login_required
def dashboard_gerente(request):
    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    
    # Filtros
    funcionario_id = request.GET.get('funcionario')
    etapa_id = request.GET.get('etapa')
    status_filtro = request.GET.get('status')
    
    # Query base de pedidos
    pedidos_query = Pedido.objects.all()
    
    # Aplicar filtros
    if funcionario_id:
        pedidos_query = pedidos_query.filter(historico_etapas__funcionario_id=funcionario_id).distinct()
    if etapa_id:
        pedidos_query = pedidos_query.filter(etapa_atual_id=etapa_id)
    if status_filtro:
        pedidos_query = pedidos_query.filter(status=status_filtro)
    
    pedidos_em_fluxo = pedidos_query.filter(status='em_fluxo').count()
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
    
    pedidos_por_etapa = pedidos_query.filter(
        status='em_fluxo'
    ).values('etapa_atual__nome').annotate(total=Count('id'))
    
    # Dados para os filtros
    from core.models import Etapa
    todas_etapas = Etapa.objects.filter(ativa=True)
    todos_funcionarios = User.objects.filter(groups__name='Funcionário')
    
    context = {
        'pedidos_em_fluxo': pedidos_em_fluxo,
        'pedidos_concluidos_mes': pedidos_concluidos_mes,
        'pontuacao_funcionarios': pontuacao_funcionarios,
        'pedidos_por_etapa': pedidos_por_etapa,
        'todas_etapas': todas_etapas,
        'todos_funcionarios': todos_funcionarios,
        'funcionario_selecionado': funcionario_id,
        'etapa_selecionada': etapa_id,
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
    from core.models import Penalizacao
    
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
    from core.models import Penalizacao
    
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
    from core.models import Penalizacao
    
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
    if not (request.user.groups.filter(name__in=['Superadmin', 'Gerente']).exists() or request.user.is_superuser):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    from django.db.models import Subquery, OuterRef, Prefetch, Q
    from django.core.paginator import Paginator
    
    # Filtros
    nome_filtro = request.GET.get('nome', '')
    nrorc_filtro = request.GET.get('nrorc', '')
    status_filtro = request.GET.get('status', '')
    etapa_filtro = request.GET.get('etapa', '')
    funcionario_filtro = request.GET.get('funcionario', '')
    
    # Subquery para pegar o último funcionário que trabalhou no pedido
    ultimo_historico = HistoricoEtapa.objects.filter(
        pedido=OuterRef('pk')
    ).order_by('-timestamp_fim').values('funcionario')[:1]
    
    # Query base
    pedidos = Pedido.objects.all().select_related(
        'etapa_atual', 
        'funcionario_na_etapa',
        'tipo'
    ).prefetch_related('historico_etapas__funcionario').annotate(
        ultimo_funcionario_id=Subquery(ultimo_historico)
    )
    
    # Aplicar filtros
    if nome_filtro:
        pedidos = pedidos.filter(nome__icontains=nome_filtro)
    if nrorc_filtro:
        pedidos = pedidos.filter(nrorc__icontains=nrorc_filtro)
    if status_filtro:
        pedidos = pedidos.filter(status=status_filtro)
    if etapa_filtro:
        pedidos = pedidos.filter(etapa_atual_id=etapa_filtro)
    if funcionario_filtro:
        pedidos = pedidos.filter(funcionario_na_etapa_id=funcionario_filtro)
    
    pedidos = pedidos.order_by('-criado_em')
    
    # Paginação
    paginator = Paginator(pedidos, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Dados para filtros
    todas_etapas = Etapa.objects.filter(ativa=True)
    todos_funcionarios = User.objects.filter(groups__name='Funcionário')
    
    context = {
        'page_obj': page_obj,
        'pedidos': page_obj.object_list,
        'todas_etapas': todas_etapas,
        'todos_funcionarios': todos_funcionarios,
        'nome_filtro': nome_filtro,
        'nrorc_filtro': nrorc_filtro,
        'status_filtro': status_filtro,
        'etapa_filtro': etapa_filtro,
        'funcionario_filtro': funcionario_filtro,
    }
    
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='outros',
        descricao='Acessou lista de pedidos',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
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
    writer.writerow(['Total de Pedidos', Pedido.objects.count()])
    writer.writerow(['Total de Usuários', User.objects.count()])
    writer.writerow(['Total de Etapas Ativas', Etapa.objects.filter(ativa=True).count()])
    writer.writerow([])
    
    # Pedidos por status
    writer.writerow(['PEDIDOS POR STATUS'])
    writer.writerow(['Status', 'Quantidade'])
    for item in Pedido.objects.values('status').annotate(total=Count('id')):
        writer.writerow([dict(Pedido.STATUS_CHOICES).get(item['status']), item['total']])
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
def perfil_funcionario(request, user_id=None):
    """Perfil completo do funcionário com pontuações, histórico e métricas"""
    from core.models import Penalizacao
    from django.core.paginator import Paginator
    
    # Se não for especificado user_id, usar o usuário logado (se for funcionário)
    if user_id:
        # Gerente ou admin vendo perfil de outro funcionário
        if not (request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() or request.user.is_superuser):
            messages.error(request, 'Acesso negado.')
            return redirect('dashboard:home')
        usuario = get_object_or_404(User, pk=user_id, groups__name='Funcionário')
    else:
        usuario = request.user
    
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
    ).select_related('pedido', 'etapa').order_by('-timestamp')
    
    # Paginação do histórico
    paginator = Paginator(historico_pontos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Resumo por origem
    resumo_origem = historico_pontos.values('origem').annotate(
        total_pontos=Sum('pontos'),
        quantidade=Count('id')
    ).order_by('-total_pontos')
    
    # Resumo por etapa
    resumo_etapa = HistoricoEtapa.objects.filter(
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
    
    total_penalizacoes = penalizacoes_mes.aggregate(total=Sum('pontos'))['total'] or Decimal('0')
    
    # Últimos 12 meses
    ultimos_meses = []
    data_atual = hoje
    
    # Mapear meses em português
    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    for i in range(12):
        mes_data = data_atual - timedelta(days=data_atual.day-1)  # Primeiro dia do mês
        
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
        
        # Voltar um mês
        if mes_data.month == 1:
            data_atual = mes_data.replace(year=mes_data.year - 1, month=12)
        else:
            data_atual = mes_data.replace(month=mes_data.month - 1)
    
    # Estatísticas gerais
    total_pontos_todos_tempos = PontuacaoFuncionario.objects.filter(
        funcionario=usuario
    ).aggregate(total=Sum('pontos'))['total'] or Decimal('0')
    
    total_pedidos_trabalhados = Pedido.objects.filter(
        historico_etapas__funcionario=usuario
    ).distinct().count()
    
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
    }
    
    return render(request, 'dashboard/perfil_funcionario.html', context)


@login_required
def lista_funcionarios(request):
    """Lista de funcionários com filtros e busca"""
    if not (request.user.groups.filter(name__in=['Gerente', 'Superadmin']).exists() or request.user.is_superuser):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    from django.core.paginator import Paginator
    
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
        'busca': busca,
        'ordenar': ordenar,
    }
    
    return render(request, 'dashboard/lista_funcionarios.html', context)


@login_required
def dashboard_superadmin(request):
    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    
    total_pedidos = Pedido.objects.count()
    total_usuarios = User.objects.count()
    total_etapas = Etapa.objects.filter(ativa=True).count()
    
    pedidos_por_status = Pedido.objects.values('status').annotate(total=Count('id'))
    
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
    
    from django.contrib import messages
    from django.db.models import Q
    from django.core.paginator import Paginator
    
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
        from datetime import datetime
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
            logs = logs.filter(timestamp__date__gte=data_inicio_obj.date())
        except ValueError:
            pass
    
    if data_fim:
        from datetime import datetime
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
        from datetime import datetime as dt
        try:
            data_inicio = dt.strptime(data_inicio_filtro, '%Y-%m-%d').date()
            formularios = formularios.filter(preenchido_em__date__gte=data_inicio)
            filtros['data_inicio'] = data_inicio_filtro
        except:
            pass
    
    if data_fim_filtro:
        from datetime import datetime as dt
        try:
            data_fim = dt.strptime(data_fim_filtro, '%Y-%m-%d').date()
            formularios = formularios.filter(preenchido_em__date__lte=data_fim)
            filtros['data_fim'] = data_fim_filtro
        except:
            pass
    
    # Paginação
    from django.core.paginator import Paginator
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
    
    import json
    funcionarios_json = json.dumps(funcionarios_json)
    
    context = {
        'formularios': formularios_page,
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
        from core.models import ConfiguracaoControleQualidade, PontuacaoFuncionario
        config = ConfiguracaoControleQualidade.get_configuracao_ativa()
        
        # Salvar pontuação total (baseada na configuração, não nas perguntas)
        formulario.pontuacao = config.pontos_por_formulario
        formulario.save()
        
        # Contabilizar pontos para o funcionário baseado na configuração
        from core.models import ConfiguracaoControleQualidade, PontuacaoFuncionario
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
