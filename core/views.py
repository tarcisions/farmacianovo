
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator


def get_grupos_disponiveis(user):
    """Retorna os grupos disponíveis para o usuário criar/editar"""
    is_admin = user.is_superuser or user.groups.filter(name='Superadmin').exists()
    is_gerente = user.groups.filter(name='Gerente').exists()
    
    if is_admin:
        return Group.objects.all().order_by('name')
    elif is_gerente:
        return Group.objects.filter(name__in=['Gerente', 'Funcionário']).order_by('name')
    return Group.objects.none()


@login_required
def usuarios_view(request):
    """Lista de usuários - Superadmin ve todos, Gerente ve apenas seus funcionários"""
    if not (request.user.groups.filter(name__in=['Superadmin', 'Gerente']).exists() or request.user.is_superuser):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard:home')
    
    if request.user.is_superuser or request.user.groups.filter(name='Superadmin').exists():
        usuarios = User.objects.all().prefetch_related('groups').order_by('-date_joined')
    else:
        # Gerente vê apenas funcionários e gerentes
        usuarios = User.objects.filter(
            groups__name__in=['Gerente', 'Funcionário']
        ).prefetch_related('groups').distinct().order_by('-date_joined')
    
    # Paginação
    paginator = Paginator(usuarios, 25)  # 25 usuários por página
    page_number = request.GET.get('page', 1)
    usuarios_paginados = paginator.get_page(page_number)
    
    grupos = Group.objects.all()
    
    context = {
        'usuarios': usuarios_paginados,
        'page_obj': usuarios_paginados,
        'is_paginated': usuarios_paginados.has_other_pages(),
        'grupos': grupos,
    }
    return render(request, 'core/usuarios.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def criar_usuario_view(request):
    """Criar novo usuário - Superadmin cria todos, Gerente cria apenas Gerentes e Funcionários"""
    
    # Verificar permissões
    is_admin = request.user.is_superuser or request.user.groups.filter(name='Superadmin').exists()
    is_gerente = request.user.groups.filter(name='Gerente').exists()
    
    if not (is_admin or is_gerente):
        messages.error(request, 'Acesso negado. Apenas Superadmin e Gerentes podem criar usuários.')
        return redirect('core:usuarios')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        grupo = request.POST.get('grupo', '').strip()
        
        # Validações
        erros = []
        
        if not username:
            erros.append('Nome de usuário é obrigatório.')
        elif User.objects.filter(username=username).exists():
            erros.append('Este nome de usuário já existe.')
        
        if not email:
            erros.append('Email é obrigatório.')
        elif User.objects.filter(email=email).exists():
            erros.append('Este email já está registrado.')
        
        if not password:
            erros.append('Senha é obrigatória.')
        elif password != confirm_password:
            erros.append('As senhas não correspondem.')
        elif len(password) < 6:
            erros.append('A senha deve ter pelo menos 6 caracteres.')
        
        if not grupo:
            erros.append('Selecione um grupo para o usuário.')
        
        # Verificar se Gerente está tentando criar Superadmin
        if is_gerente and not is_admin:
            if grupo == 'Superadmin':
                erros.append('Gerentes não podem criar Superadmins.')
        
        # Validar grupo
        try:
            grupo_obj = Group.objects.get(name=grupo)
        except Group.DoesNotExist:
            erros.append(f'O grupo {grupo} não existe.')
            grupo_obj = None
        
        if erros:
            context = {
                'erros': erros,
                'grupos_disponiveis': get_grupos_disponiveis(request.user),
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            }
            return render(request, 'core/criar_usuario.html', context)
        
        # Criar usuário
        usuario = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        
        if grupo_obj:
            usuario.groups.add(grupo_obj)
        
        # Se for Gerente, marcar como staff
        if grupo == 'Gerente':
            usuario.is_staff = True
            usuario.save()
        
        messages.success(request, f'Usuário {username} criado com sucesso!')
        return redirect('core:usuarios')
    
    # GET - mostrar formulário
    context = {
        'grupos_disponiveis': get_grupos_disponiveis(request.user),
    }
    return render(request, 'core/criar_usuario.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def editar_usuario_view(request, user_id):
    """Editar usuário existente"""
    usuario = get_object_or_404(User, pk=user_id)
    
    # Verificar permissões
    is_admin = request.user.is_superuser or request.user.groups.filter(name='Superadmin').exists()
    is_gerente = request.user.groups.filter(name='Gerente').exists()
    
    # Gerente não pode editar Superadmin
    if is_gerente and not is_admin:
        if usuario.groups.filter(name='Superadmin').exists() or usuario.is_superuser:
            messages.error(request, 'Gerentes não podem editar Superadmins.')
            return redirect('core:usuarios')
    
    if not (is_admin or is_gerente):
        messages.error(request, 'Acesso negado.')
        return redirect('core:usuarios')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        grupo = request.POST.get('grupo', '').strip()
        ativo = request.POST.get('ativo') == 'on'
        
        erros = []
        
        if email and email != usuario.email and User.objects.filter(email=email).exists():
            erros.append('Este email já está registrado.')
        
        if grupo:
            try:
                grupo_obj = Group.objects.get(name=grupo)
            except Group.DoesNotExist:
                erros.append(f'O grupo {grupo} não existe.')
                grupo_obj = None
        else:
            grupo_obj = None
        
        if erros:
            grupos_disponiveis = get_grupos_disponiveis(request.user)
            grupo_atual = usuario.groups.first().name if usuario.groups.exists() else ''
            context = {
                'erros': erros,
                'usuario': usuario,
                'grupos_disponiveis': grupos_disponiveis,
                'grupo_atual': grupo_atual,
            }
            return render(request, 'core/editar_usuario.html', context)
        
        # Atualizar usuário
        usuario.email = email
        usuario.first_name = first_name
        usuario.last_name = last_name
        usuario.is_active = ativo
        usuario.save()
        
        # Atualizar grupo
        if grupo_obj:
            usuario.groups.clear()
            usuario.groups.add(grupo_obj)
            
            # Se for Gerente, marcar como staff
            if grupo == 'Gerente':
                usuario.is_staff = True
            else:
                usuario.is_staff = False
            usuario.save()
        
        messages.success(request, f'Usuário {usuario.username} atualizado com sucesso!')
        return redirect('core:usuarios')
    
    # GET - mostrar formulário
    grupo_atual = usuario.groups.first().name if usuario.groups.exists() else ''
    grupos_disponiveis = get_grupos_disponiveis(request.user)
    
    context = {
        'usuario': usuario,
        'grupo_atual': grupo_atual,
        'grupos_disponiveis': grupos_disponiveis,
    }
    return render(request, 'core/editar_usuario.html', context)


@login_required
def deletar_usuario_view(request, user_id):
    """Deletar usuário"""
    if request.method != 'POST':
        return redirect('core:usuarios')
    
    usuario = get_object_or_404(User, pk=user_id)
    
    # Verificar permissões
    is_admin = request.user.is_superuser or request.user.groups.filter(name='Superadmin').exists()
    
    if not is_admin:
        messages.error(request, 'Acesso negado. Apenas Superadmin pode deletar usuários.')
        return redirect('core:usuarios')
    
    if usuario == request.user:
        messages.error(request, 'Você não pode deletar a sua própria conta.')
        return redirect('core:usuarios')
    
    username = usuario.username
    usuario.delete()
    messages.success(request, f'Usuário {username} deletado com sucesso!')
    return redirect('core:usuarios')
