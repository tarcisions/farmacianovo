from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password


@login_required
def meu_perfil(request):
    """Página do perfil do usuário logado"""
    usuario = request.user
    
    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'editar_perfil':
            # Editar informações pessoais
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            
            # Validações
            if not first_name:
                messages.error(request, 'Nome é obrigatório.')
                return redirect('core:meu_perfil')
            
            if not last_name:
                messages.error(request, 'Sobrenome é obrigatório.')
                return redirect('core:meu_perfil')
            
            if not email:
                messages.error(request, 'Email é obrigatório.')
                return redirect('core:meu_perfil')
            
            # Verificar se email já existe em outro usuário
            if User.objects.filter(email=email).exclude(id=usuario.id).exists():
                messages.error(request, 'Este email já está registrado.')
                return redirect('core:meu_perfil')
            
            # Atualizar usuário
            usuario.first_name = first_name
            usuario.last_name = last_name
            usuario.email = email
            usuario.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('core:meu_perfil')
        
        elif acao == 'trocar_senha':
            # Trocar senha
            senha_atual = request.POST.get('senha_atual', '')
            senha_nova = request.POST.get('senha_nova', '')
            confirmar_senha = request.POST.get('confirmar_senha', '')
            
            # Validações
            if not check_password(senha_atual, usuario.password):
                messages.error(request, 'Senha atual incorreta.')
                return redirect('core:meu_perfil')
            
            if not senha_nova:
                messages.error(request, 'Nova senha é obrigatória.')
                return redirect('core:meu_perfil')
            
            if senha_nova != confirmar_senha:
                messages.error(request, 'As senhas não correspondem.')
                return redirect('core:meu_perfil')
            
            if len(senha_nova) < 6:
                messages.error(request, 'A senha deve ter pelo menos 6 caracteres.')
                return redirect('core:meu_perfil')
            
            # Atualizar senha
            usuario.set_password(senha_nova)
            usuario.save()
            update_session_auth_hash(request, usuario)
            messages.success(request, 'Senha alterada com sucesso!')
            return redirect('core:meu_perfil')
    
    # Obter grupos do usuário
    grupos = usuario.groups.values_list('name', flat=True)
    
    context = {
        'usuario': usuario,
        'grupos': list(grupos),
    }
    
    return render(request, 'core/meu_perfil.html', context)
