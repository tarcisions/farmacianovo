from django.core.management.base import BaseCommand
from core.models import Etapa, ControlePergunta, ControlePerguntaOpcao


class Command(BaseCommand):
    help = 'Cria perguntas de exemplo para Controle de Qualidade'

    def handle(self, *args, **options):
        # Obter a etapa "Controle de Qualidade"
        try:
            etapa_cq = Etapa.objects.get(nome__iexact='Controle de Qualidade')
            self.stdout.write(self.style.SUCCESS(f'✅ Etapa encontrada: {etapa_cq}'))
        except Etapa.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Etapa 'Controle de Qualidade' nao encontrada!"))
            return

        # Lista de perguntas a criar
        perguntas_dados = [
            {
                'pergunta': 'Conferiu todos os produtos?',
                'tipo_campo': 'checkbox',
                'descricao': 'Verifique se todos os itens estao presente e intactos',
                'ordem': 1,
                'obrigatorio': True,
                'opcoes': ['Sim', 'Nao', 'Parcialmente']
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
                'pergunta': 'Qual e o nivel de qualidade do produto?',
                'tipo_campo': 'selecao',
                'descricao': 'Avalie o padrao geral de qualidade',
                'ordem': 4,
                'obrigatorio': True,
                'opcoes': ['Excelente', 'Bom', 'Aceitavel', 'Rejeitado']
            },
            {
                'pergunta': 'Quantidade de itens inspecionados',
                'tipo_campo': 'numero',
                'descricao': 'Quantos itens voce verificou neste lote?',
                'ordem': 5,
                'obrigatorio': True,
                'opcoes': None
            },
            {
                'pergunta': 'Data de validade (se aplicavel)',
                'tipo_campo': 'texto',
                'descricao': 'Registre a data de validade ou expiracao do produto',
                'ordem': 6,
                'obrigatorio': False,
                'opcoes': None
            },
        ]

        # Criar as perguntas
        perguntas_criadas = 0
        for dados in perguntas_dados:
            pergunta_texto = dados['pergunta']
            
            # Verificar se ja existe
            if ControlePergunta.objects.filter(etapa=etapa_cq, pergunta=pergunta_texto).exists():
                self.stdout.write(f'⏭️  Pergunta ja existe: {pergunta_texto}')
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
            
            self.stdout.write(self.style.SUCCESS(f'✅ Pergunta criada: {pergunta_texto}'))
            
            # Criar opcoes se houver
            if dados['opcoes']:
                for idx, opcao_texto in enumerate(dados['opcoes'], 1):
                    opcao = ControlePerguntaOpcao.objects.create(
                        pergunta=pergunta,
                        texto_opcao=opcao_texto,
                        ordem=idx
                    )
                    self.stdout.write(f'   └─ Opcao: {opcao_texto}')
            
            perguntas_criadas += 1

        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'✅ SUCESSO! {perguntas_criadas} perguntas criadas com sucesso!'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(self.style.WARNING(f'\n📋 Perguntas criadas:'))
        self.stdout.write(f'  1. Conferiu todos os produtos? (Checkbox)')
        self.stdout.write(f'  2. Houve algum dano visual? (Checkbox)')
        self.stdout.write(f'  3. Descreva problemas encontrados (Textarea)')
        self.stdout.write(f'  4. Nivel de qualidade (Selecao)')
        self.stdout.write(f'  5. Quantidade inspecionada (Numero)')
        self.stdout.write(f'  6. Data de validade (Texto)')
        self.stdout.write(self.style.SUCCESS(f'\n🚀 Agora voce pode testar o formulario!'))
