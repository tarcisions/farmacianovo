
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from core.models import Etapa, Pedido, Checklist
from django.utils import timezone

@login_required
def lista_etapas(request):
    if not (request.user.groups.filter(name__in=['Superadmin', 'Gerente']).exists() or request.user.is_superuser):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    etapas = Etapa.objects.all().order_by('sequencia')
    
    context = {
        'etapas': etapas,
    }
    return render(request, 'workflow/etapas.html', context)

@login_required
def lista_checklists(request):
    if not (request.user.groups.filter(name__in=['Superadmin', 'Gerente']).exists() or request.user.is_superuser):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    checklists = Checklist.objects.all().select_related('etapa')
    
    context = {
        'checklists': checklists,
    }
    return render(request, 'workflow/checklists.html', context)
