#!/usr/bin/env python
"""
Script para criar perguntas de exemplo para Controle de Qualidade
Execute com: python manage.py shell < criar_perguntas_exemplo.py
"""

from core.models import Etapa, ControlePergunta, ControlePerguntaOpcao

# Obter a etapa "Controle de Qualidade"
try:
    etapa_cq = Etapa.objects.get(nome__iexact='Controle de Qualidade')
    print(f"✅ Etapa encontrada: {etapa_cq}")
except Etapa.DoesNotExist:
    print("❌ Etapa 'Controle de Qualidade' não encontrada!")
    exit(1)

# Limpar perguntas anteriores (opcional)
# ControlePergunta.objects.filter(etapa=etapa_cq).delete()
# print("Perguntas anteriores removidas")

# Lista de perguntas a criar
perguntas_dados = [
    {
        'pergunta': 'Conferiu todos os produtos?',
        'tipo_campo': 'checkbox',
        'descricao': 'Verifique se todos os itens estão presente e intactos',
        'ordem': 1,
        'obrigatorio': True,
        'opcoes': ['Sim', 'Não', 'Parcialmente']
    },
    {
        'pergunta': 'Houve algum dano visual no produto?',
        'tipo_campo': 'checkbox',
        'descricao': 'Procure por danos, amassados, fissuras ou outros problemas',
        'ordem': 2,
        'obrigatorio': True,
        'opcoes': ['Nenhum dano', 'Dano menor', 'Dano grave']
    },
    {
        'pergunta': 'Descreva qualquer problema encontrado',
        'tipo_campo': 'textarea',
        'descricao': 'Se encontrou algum problema, descreva detalhadamente aqui',
        'ordem': 3,
        'obrigatorio': False,
        'opcoes': None
    },
    {
        'pergunta': 'Qual é o nível de qualidade do produto?',
        'tipo_campo': 'selecao',
        'descricao': 'Avalie o padrão geral de qualidade',
        'ordem': 4,
        'obrigatorio': True,
        'opcoes': ['Excelente', 'Bom', 'Aceitável', 'Rejeitado']
    },
    {
        'pergunta': 'Quantidade de itens inspecionados',
        'tipo_campo': 'numero',
        'descricao': 'Quantos itens você verificou neste lote?',
        'ordem': 5,
        'obrigatorio': True,
        'opcoes': None
    },
    {
        'pergunta': 'Data de validade (se aplicável)',
        'tipo_campo': 'texto',
        'descricao': 'Registre a data de validade ou expiração do produto',
        'ordem': 6,
        'obrigatorio': False,
        'opcoes': None
    },
]

# Criar as perguntas
perguntas_criadas = 0
for dados in perguntas_dados:
    pergunta_texto = dados['pergunta']
    
    # Verificar se já existe
    if ControlePergunta.objects.filter(etapa=etapa_cq, pergunta=pergunta_texto).exists():
        print(f"⏭️  Pergunta já existe: {pergunta_texto}")
        continue
    
    # Criar pergunta
    pergunta = ControlePergunta.objects.create(
        etapa=etapa_cq,
        pergunta=pergunta_texto,
        tipo_campo=dados['tipo_campo'],
        descricao=dados['descricao'],
        ordem=dados['ordem'],
        obrigatorio=dados['obrigatorio'],
        ativo=True
    )
    
    print(f"✅ Pergunta criada: {pergunta_texto}")
    
    # Criar opções se houver
    if dados['opcoes']:
        for idx, opcao_texto in enumerate(dados['opcoes'], 1):
            opcao = ControlePerguntaOpcao.objects.create(
                pergunta=pergunta,
                texto_opcao=opcao_texto,
                ordem=idx
            )
            print(f"   └─ Opção: {opcao_texto}")
    
    perguntas_criadas += 1

print(f"\n{'='*60}")
print(f"✅ SUCESSO! {perguntas_criadas} perguntas criadas com sucesso!")
print(f"{'='*60}")
print(f"\n📋 Perguntas criadas:")
print(f"  1. Conferiu todos os produtos? (Checkbox)")
print(f"  2. Houve algum dano visual? (Checkbox)")
print(f"  3. Descreva problemas encontrados (Textarea)")
print(f"  4. Nível de qualidade (Seleção)")
print(f"  5. Quantidade inspecionada (Número)")
print(f"  6. Data de validade (Texto)")
print(f"\n🚀 Agora você pode testar o formulário!")
