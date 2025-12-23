
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from core.models import Etapa, Pedido, Checklist
from django.utils import timezone
from .forms import EtapaForm, ChecklistForm

def check_admin_permission(user):
    """Verifica se o usuário é admin/gerente/superadmin"""
    return (user.groups.filter(name__in=['Superadmin', 'Gerente']).exists() or user.is_superuser)

@login_required
def lista_etapas(request):
    if not check_admin_permission(request.user):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    etapas = Etapa.objects.all().order_by('sequencia')
    
    context = {
        'etapas': etapas,
    }
    return render(request, 'workflow/etapas.html', context)

@login_required
def criar_etapa(request):
    if not check_admin_permission(request.user):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = EtapaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Etapa criada com sucesso!')
            return redirect('workflow:lista_etapas')
    else:
        form = EtapaForm()
    
    context = {
        'form': form,
        'titulo': 'Criar Nova Etapa',
    }
    return render(request, 'workflow/form_etapa.html', context)

@login_required
def editar_etapa(request, id):
    if not check_admin_permission(request.user):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    etapa = get_object_or_404(Etapa, id=id)
    
    if request.method == 'POST':
        form = EtapaForm(request.POST, instance=etapa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Etapa atualizada com sucesso!')
            return redirect('workflow:lista_etapas')
    else:
        form = EtapaForm(instance=etapa)
    
    context = {
        'form': form,
        'titulo': f'Editar Etapa: {etapa.nome}',
        'etapa': etapa,
    }
    return render(request, 'workflow/form_etapa.html', context)

@login_required
def deletar_etapa(request, id):
    if not check_admin_permission(request.user):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    etapa = get_object_or_404(Etapa, id=id)
    
    if request.method == 'POST':
        nome = etapa.nome
        etapa.delete()
        messages.success(request, f'Etapa "{nome}" deletada com sucesso!')
        return redirect('workflow:lista_etapas')
    
    context = {
        'etapa': etapa,
    }
    return render(request, 'workflow/confirmar_deletar_etapa.html', context)

@login_required
def checklists_etapa(request, etapa_id):
    """Lista todos os checklists de uma etapa específica"""
    if not check_admin_permission(request.user):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    etapa = get_object_or_404(Etapa, id=etapa_id)
    checklists = etapa.checklists.all().order_by('ordem', 'id')
    
    context = {
        'etapa': etapa,
        'checklists': checklists,
    }
    return render(request, 'workflow/checklists_etapa.html', context)

@login_required
def criar_checklist_etapa(request, etapa_id):
    """Criar novo checklist para uma etapa específica"""
    if not check_admin_permission(request.user):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    etapa = get_object_or_404(Etapa, id=etapa_id)
    
    if request.method == 'POST':
        form = ChecklistForm(request.POST)
        if form.is_valid():
            checklist = form.save(commit=False)
            checklist.etapa = etapa
            checklist.save()
            messages.success(request, 'Checklist criado com sucesso!')
            return redirect('workflow:checklists_etapa', etapa_id=etapa.id)
    else:
        form = ChecklistForm()
    
    context = {
        'form': form,
        'etapa': etapa,
        'titulo': f'Criar Checklist para: {etapa.nome}',
    }
    return render(request, 'workflow/form_checklist.html', context)

@login_required
def editar_checklist(request, checklist_id):
    """Editar um checklist existente"""
    if not check_admin_permission(request.user):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    checklist = get_object_or_404(Checklist, id=checklist_id)
    etapa = checklist.etapa
    
    if request.method == 'POST':
        form = ChecklistForm(request.POST, instance=checklist)
        if form.is_valid():
            form.save()
            messages.success(request, 'Checklist atualizado com sucesso!')
            return redirect('workflow:checklists_etapa', etapa_id=etapa.id)
    else:
        form = ChecklistForm(instance=checklist)
    
    context = {
        'form': form,
        'etapa': etapa,
        'checklist': checklist,
        'titulo': f'Editar Checklist: {checklist.nome}',
    }
    return render(request, 'workflow/form_checklist.html', context)

@login_required
def deletar_checklist(request, checklist_id):
    """Deletar um checklist"""
    if not check_admin_permission(request.user):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    checklist = get_object_or_404(Checklist, id=checklist_id)
    etapa = checklist.etapa
    
    if request.method == 'POST':
        nome = checklist.nome
        checklist.delete()
        messages.success(request, f'Checklist "{nome}" deletado com sucesso!')
        return redirect('workflow:checklists_etapa', etapa_id=etapa.id)
    
    context = {
        'checklist': checklist,
        'etapa': etapa,
    }
    return render(request, 'workflow/confirmar_deletar_checklist.html', context)

@login_required
def lista_checklists(request):
    if not check_admin_permission(request.user):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    checklists = Checklist.objects.all().select_related('etapa')
    
    context = {
        'checklists': checklists,
    }
    return render(request, 'workflow/checklists.html', context)