from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.utils import timezone
from core.models import (
    Etapa, Laboratorio, TipoProduto, PontuacaoPorAtividade,
    ConfiguracaoPontuacao, Checklist, BonusFaixa,
    ConfiguracaoExpedicao, PontuacaoFixaMensal
)
from decimal import Decimal

class Command(BaseCommand):
    help = 'Setup inicial do sistema: grupos, usuários, etapas, laboratórios e pontuações'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando setup...')
        
        # Criar grupos
        funcionario_group, _ = Group.objects.get_or_create(name='Funcionário')
        gerente_group, _ = Group.objects.get_or_create(name='Gerente')
        superadmin_group, _ = Group.objects.get_or_create(name='Superadmin')
        
        self.stdout.write(self.style.SUCCESS('Grupos criados'))
        
        # Criar usuários
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@sistema.com',
                password='admin123',
                first_name='Administrador',
                last_name='Sistema'
            )
            admin.groups.add(superadmin_group)
            self.stdout.write(self.style.SUCCESS('Superusuário criado: admin / admin123'))
        
        if not User.objects.filter(username='gerente').exists():
            gerente = User.objects.create_user(
                username='gerente',
                email='gerente@sistema.com',
                password='gerente123',
                first_name='João',
                last_name='Silva'
            )
            gerente.groups.add(gerente_group)
            gerente.is_staff = True
            gerente.save()
            self.stdout.write(self.style.SUCCESS('Gerente criado: gerente / gerente123'))
        
        # Criar 3 funcionários de teste
        funcionarios_teste = [
            {'username': 'func_maria', 'email': 'maria@sistema.com', 'first_name': 'Maria', 'last_name': 'Santos'},
            {'username': 'func_carlos', 'email': 'carlos@sistema.com', 'first_name': 'Carlos', 'last_name': 'Silva'},
            {'username': 'func_ana', 'email': 'ana@sistema.com', 'first_name': 'Ana', 'last_name': 'Costa'},
        ]
        
        for func_data in funcionarios_teste:
            if not User.objects.filter(username=func_data['username']).exists():
                func = User.objects.create_user(
                    username=func_data['username'],
                    email=func_data['email'],
                    password='func123',
                    first_name=func_data['first_name'],
                    last_name=func_data['last_name']
                )
                func.groups.add(funcionario_group)
                func.save()
                self.stdout.write(self.style.SUCCESS(f"Funcionário criado: {func_data['username']} / func123"))
        
        # Criar Etapas
        if not Etapa.objects.exists():
            etapas_config = [
                {'nome': 'Triagem', 'sequencia': 1, 'grupo': 'triagem', 'se_gera_pontos': False, 'se_possui_checklists': False},
                {'nome': 'Produção', 'sequencia': 2, 'grupo': 'producao', 'se_gera_pontos': True, 'se_possui_checklists': True},
                {'nome': 'Conf/Rotulagem', 'sequencia': 3, 'grupo': 'conf_rotulagem', 'se_gera_pontos': True, 'se_possui_checklists': True},
                {'nome': 'Expedição', 'sequencia': 4, 'grupo': 'expedicao', 'se_gera_pontos': True, 'se_possui_checklists': True},
            ]
            
            etapas = {}
            for etapa_data in etapas_config:
                etapa = Etapa.objects.create(**etapa_data)
                etapas[etapa.nome] = etapa
                ConfiguracaoPontuacao.objects.create(
                    etapa=etapa,
                    pontos_fixos=Decimal('0.00'),
                    pontos_por_check=Decimal('0.00'),
                    versao='1.0',
                    ativa=True
                )
            
            self.stdout.write(self.style.SUCCESS('Etapas criadas'))
        else:
            etapas = {e.nome: e for e in Etapa.objects.all()}
        
        # Criar Laboratórios
        if not Laboratorio.objects.exists():
            lab_capsula = Laboratorio.objects.create(
                tipo='capsula_sache',
                nome='Laboratório de Cápsulas e Sachês',
                descricao='Responsável pela produção de cápsulas e sachês'
            )
            lab_pediatrico = Laboratorio.objects.create(
                tipo='pediatrico',
                nome='Laboratório Pediátrico',
                descricao='Responsável pela produção de formulações pediátricas'
            )
            lab_externo = Laboratorio.objects.create(
                tipo='externo',
                nome='Laboratório Externo',
                descricao='Responsável pela produção de cosméticos e outros'
            )
            self.stdout.write(self.style.SUCCESS('Laboratórios criados'))
        else:
            lab_capsula = Laboratorio.objects.get(tipo='capsula_sache')
            lab_pediatrico = Laboratorio.objects.get(tipo='pediatrico')
            lab_externo = Laboratorio.objects.get(tipo='externo')
        
        # Criar Tipos de Produtos
        if not TipoProduto.objects.exists():
            tipos = [
                # Laboratório de Cápsulas e Sachês
                {'tipo': 'capsula', 'nome': 'Cápsula', 'laboratorio': lab_capsula},
                {'tipo': 'sache', 'nome': 'Sachê', 'laboratorio': lab_capsula},
                # Laboratório Pediátrico
                {'tipo': 'liquido_pediatrico', 'nome': 'Líquido Pediátrico', 'laboratorio': lab_pediatrico},
                # Laboratório Externo
                {'tipo': 'lotion', 'nome': 'Loção', 'laboratorio': lab_externo},
                {'tipo': 'creme', 'nome': 'Creme', 'laboratorio': lab_externo},
                {'tipo': 'shampoo', 'nome': 'Shampoo', 'laboratorio': lab_externo},
                {'tipo': 'shot', 'nome': 'Shot', 'laboratorio': lab_externo},
                {'tipo': 'ovulo', 'nome': 'Óvulo', 'laboratorio': lab_externo},
                {'tipo': 'comprimido_sublingual', 'nome': 'Comprimido Sublingual', 'laboratorio': lab_externo},
                {'tipo': 'capsula_oleosa', 'nome': 'Cápsula Oleosa', 'laboratorio': lab_externo},
                {'tipo': 'goma', 'nome': 'Goma', 'laboratorio': lab_externo},
                {'tipo': 'chocolate', 'nome': 'Chocolate', 'laboratorio': lab_externo},
                {'tipo': 'filme', 'nome': 'Filme', 'laboratorio': lab_externo},
            ]
            
            tipos_dict = {}
            for tipo_data in tipos:
                tipo = TipoProduto.objects.create(**tipo_data)
                tipos_dict[tipo.tipo] = tipo
            
            self.stdout.write(self.style.SUCCESS('Tipos de Produtos criados'))
        else:
            tipos_dict = {t.tipo: t for t in TipoProduto.objects.all()}
        
        # Criar Pontuações por Atividade
        if not PontuacaoPorAtividade.objects.exists():
            etapa_producao = etapas.get('Produção')
            etapa_conf = etapas.get('Conf/Rotulagem')
            
            pontuacoes = [
                # 2.1 Laboratório de cápsulas - Pesagem
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('capsula'), 'atividade': 'pesagem', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('0.5')},
                # 2.1 Laboratório de cápsulas - Encapsulação
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('capsula'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 60, 'pontos_por_formula': Decimal('1.0')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('capsula'), 'atividade': 'encapsulacao', 'faixa_min': 61, 'faixa_max': 120, 'pontos_por_formula': Decimal('1.5')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('capsula'), 'atividade': 'encapsulacao', 'faixa_min': 121, 'faixa_max': 240, 'pontos_por_formula': Decimal('2.0')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('capsula'), 'atividade': 'encapsulacao', 'faixa_min': 241, 'faixa_max': 999999, 'pontos_por_formula': Decimal('3.0')},
                
                # 2.2 Sachês
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('sache'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 60, 'pontos_por_formula': Decimal('2.0')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('sache'), 'atividade': 'encapsulacao', 'faixa_min': 61, 'faixa_max': 999999, 'pontos_por_formula': Decimal('3.0')},
                
                # 2.3 Laboratório pediátrico
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('liquido_pediatrico'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('1.0')},
                
                # 2.4 Laboratório externo
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('lotion'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('1.0')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('creme'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('1.0')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('shampoo'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('1.0')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('shot'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('1.5')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('ovulo'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('1.5')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('comprimido_sublingual'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('1.5')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('capsula_oleosa'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('2.0')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('goma'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('2.0')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('chocolate'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('2.0')},
                {'etapa': etapa_producao, 'tipo_produto': tipos_dict.get('filme'), 'atividade': 'encapsulacao', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('2.0')},
                
                # 2.7 Rotulagem, conferência e reconferência
                {'etapa': etapa_conf, 'tipo_produto': None, 'atividade': 'rotulagem', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('0.3')},
                {'etapa': etapa_conf, 'tipo_produto': None, 'atividade': 'conferencia', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('0.3')},
                {'etapa': etapa_conf, 'tipo_produto': None, 'atividade': 'reconferencia', 'faixa_min': 0, 'faixa_max': 999999, 'pontos_por_formula': Decimal('0.3')},
            ]
            
            for pont_data in pontuacoes:
                PontuacaoPorAtividade.objects.create(**pont_data)
            
            self.stdout.write(self.style.SUCCESS('Pontuações por Atividade criadas'))
        
        # Criar Checklists para as etapas
        if not Checklist.objects.exists():
            etapa_producao = etapas.get('Produção')
            etapa_conf = etapas.get('Conf/Rotulagem')
            etapa_expedicao = etapas.get('Expedição')
            
            checklists = [
                # Produção
                {'etapa': etapa_producao, 'nome': 'Matéria-prima verificada', 'pontos_do_check': Decimal('0'), 'obrigatorio': True, 'ordem': 1},
                {'etapa': etapa_producao, 'nome': 'Produção iniciada', 'pontos_do_check': Decimal('0'), 'obrigatorio': True, 'ordem': 2},
                {'etapa': etapa_producao, 'nome': 'Produção concluída', 'pontos_do_check': Decimal('0'), 'obrigatorio': True, 'ordem': 3},
                
                # Conf/Rotulagem
                {'etapa': etapa_conf, 'nome': 'Rotulagem realizada', 'pontos_do_check': Decimal('0'), 'obrigatorio': True, 'ordem': 1},
                {'etapa': etapa_conf, 'nome': 'Conferência concluída', 'pontos_do_check': Decimal('0'), 'obrigatorio': True, 'ordem': 2},
                {'etapa': etapa_conf, 'nome': 'Reconferência concluída', 'pontos_do_check': Decimal('0'), 'obrigatorio': False, 'ordem': 3},
                
                # Expedição
                {'etapa': etapa_expedicao, 'nome': 'ROTA MOTOBOY', 'pontos_do_check': Decimal('15'), 'obrigatorio': False, 'ordem': 1},
                {'etapa': etapa_expedicao, 'nome': 'SEDEX', 'pontos_do_check': Decimal('15'), 'obrigatorio': False, 'ordem': 2},
            ]
            
            for check_data in checklists:
                Checklist.objects.create(**check_data)
            
            self.stdout.write(self.style.SUCCESS('Checklists criados'))
        
        # Criar Faixas de Bônus
        if not BonusFaixa.objects.exists():
            BonusFaixa.objects.create(faixa_min=Decimal('0'), faixa_max=Decimal('400'), valor_em_reais=Decimal('0.00'))
            BonusFaixa.objects.create(faixa_min=Decimal('401'), faixa_max=Decimal('600'), valor_em_reais=Decimal('150.00'))
            BonusFaixa.objects.create(faixa_min=Decimal('601'), faixa_max=Decimal('800'), valor_em_reais=Decimal('250.00'))
            BonusFaixa.objects.create(faixa_min=Decimal('801'), faixa_max=None, valor_em_reais=Decimal('350.00'))
            self.stdout.write(self.style.SUCCESS('Faixas de bônus criadas'))
        
        # Criar Pontuações Fixas Mensais
        if not PontuacaoFixaMensal.objects.exists():
            etapa_producao = etapas.get('Produção')
            etapa_expedicao = etapas.get('Expedição')
            
            PontuacaoFixaMensal.objects.create(
                nome_regra='Análise completa (matéria-prima ou fórmula)',
                valor=Decimal('3.00'),
                tipo_aplicacao='manual_gerente',
                etapa_relacionada=etapa_producao
            )
            PontuacaoFixaMensal.objects.create(
                nome_regra='Organização do estoque (contagem, etiquetagem e disposição)',
                valor=Decimal('200.00'),
                tipo_aplicacao='manual_gerente',
                etapa_relacionada=etapa_producao
            )
            PontuacaoFixaMensal.objects.create(
                nome_regra='Rota montada para motoboy',
                valor=Decimal('15.00'),
                tipo_aplicacao='manual_gerente',
                etapa_relacionada=etapa_expedicao
            )
            PontuacaoFixaMensal.objects.create(
                nome_regra='Dia de sedex despachado e organizado',
                valor=Decimal('15.00'),
                tipo_aplicacao='manual_gerente',
                etapa_relacionada=etapa_expedicao
            )
            self.stdout.write(self.style.SUCCESS('Pontuações Fixas Mensais criadas'))
        
        # Criar Configurações de Expedição
        if not ConfiguracaoExpedicao.objects.exists():
            ConfiguracaoExpedicao.objects.create(
                tipo_expedicao='motoboy',
                pontos_por_rota_motoboy=Decimal('15.00'),
            )
            ConfiguracaoExpedicao.objects.create(
                tipo_expedicao='sedex',
                tipo_pontuacao_sedex='por_dia',
                pontos_sedex=Decimal('15.00')
            )
            self.stdout.write(self.style.SUCCESS('Configurações de expedição criadas'))
        
        self.stdout.write(self.style.SUCCESS('Setup concluído com sucesso!'))

