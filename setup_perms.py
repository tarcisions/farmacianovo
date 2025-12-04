#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'producao_gamificada.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import (
    Checklist, Etapa, Laboratorio, TipoProduto, 
    PontuacaoPorAtividade, ConfiguracaoPontuacao,
    Pedido, HistoricoEtapa, ChecklistExecucao,
    PontuacaoFuncionario, Penalizacao,
    PontuacaoFixaMensal, HistoricoAplicacaoPontuacaoFixa,
    BonusFaixa, HistoricoBonusMensal,
    ConfiguracaoExpedicao, RegistroExpedicao
)

# Modelos que Gerente pode acessar no admin
GERENTE_MODELS = [
    Etapa,
    Checklist,
    Pedido,
    HistoricoEtapa,
    ChecklistExecucao,
    PontuacaoFuncionario,
    ConfiguracaoPontuacao,
    ConfiguracaoExpedicao,
    RegistroExpedicao,
]

gerente_group = Group.objects.filter(name='Gerente').first()
if not gerente_group:
    print("Grupo Gerente não existe!")
    exit(1)

print(f"Configurando permissões para Gerente...")
added_count = 0

for model in GERENTE_MODELS:
    ct = ContentType.objects.get_for_model(model)
    perms = Permission.objects.filter(content_type=ct)
    for perm in perms:
        if perm not in gerente_group.permissions.all():
            gerente_group.permissions.add(perm)
            added_count += 1
            print(f"  ✓ {model.__name__}.{perm.codename}")

print(f"\nTotal de {added_count} permissões adicionadas ao Gerente!")
print("✅ Gerente agora pode gerenciar Checklists, Pedidos, Etapas, etc.")
