import requests
import re
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from core.models import Pedido, Etapa, TipoProduto
from decimal import Decimal
from datetime import datetime


class Command(BaseCommand):
    help = 'Sincroniza pedidos da API externa com o banco de dados'
    
    # Mapeamento de status da API para etapas
    STATUS_ETAPA_MAP = {
        1: 'triagem',        # IDSTATUSITEMPEDIDO: 1 -> Triagem
        2: 'producao',       # IDSTATUSITEMPEDIDO: 2 -> Produção
        3: 'conf_rotulagem', # IDSTATUSITEMPEDIDO: 3 -> Conf/Rotulagem
        4: 'expedicao',      # IDSTATUSITEMPEDIDO: 4 -> Expedição
    }
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--pagina',
            type=int,
            default=1,
            help='Número da página para sincronizar'
        )
        parser.add_argument(
            '--tamanho',
            type=int,
            default=50,
            help='Quantidade de registros por página'
        )
    
    @staticmethod
    def extrair_quantidade_produto(descricao_web):
        """
        Extrai a quantidade de unidades do produto APENAS de CAPSULA e ENVELOPE
        Busca pelos padrões: "CAPSULA: XXcap" ou "ENVELOPE: XXenv"
        Exemplos:
            "FORMULA MANIPULADA - CAPSULA: 30CAP | ..." -> 30
            "FORMULA MANIPULADA - ENVELOPE: 10ENV | ..." -> 10
            "5ML | PALMITATO DE RETINOL LIQUIDO..." -> None (não extrai ML)
        Retorna: int ou None se não encontrar
        """
        if not descricao_web:
            return None
        
        descricao_upper = descricao_web.upper()
        
        # Padrão 1: "CAPSULA: XXcap" (apenas após a palavra CAPSULA:)
        match = re.search(r'CAPSULA\s*:\s*(\d+)\s*CAP', descricao_upper)
        if match:
            try:
                quantidade = int(match.group(1))
                return quantidade if quantidade > 0 else None
            except (ValueError, AttributeError):
                return None
        
        # Padrão 2: "ENVELOPE: XXenv" (apenas após a palavra ENVELOPE:)
        match = re.search(r'ENVELOPE\s*:\s*(\d+)\s*ENV', descricao_upper)
        if match:
            try:
                quantidade = int(match.group(1))
                return quantidade if quantidade > 0 else None
            except (ValueError, AttributeError):
                return None
        
        return None
    
    @staticmethod
    def extrair_tipo_produto(descricao_web):
        """
        Extrai o tipo de produto da descrição
        Retorna: (tipo_produto_object ou None, tipo_identificado)
        """
        if not descricao_web:
            return None, 'desconhecido'
        
        descricao_upper = descricao_web.upper()
        
        # Padrões para identificar tipos de produtos
        padroes = {
            'capsula': {
                'palavras': ['CAPSULA', 'CAP'],
                'tipo': 'capsula'
            },
            'sache': {
                'palavras': ['SACHE', 'SACHÊ', 'ENVELOPE'],
                'tipo': 'sache'
            },
            'liquido': {
                'palavras': ['ML', 'LIQUIDO', 'LÍQUIDO', 'XAROPE', 'XAROPE CLEAN', 'TCM LIQUIDO'],
                'tipo': 'liquido_pediatrico'
            },
            'creme': {
                'palavras': ['CREME', 'POMADA', 'PENTRAVAN'],
                'tipo': 'creme'
            },
            'lotion': {
                'palavras': ['LOÇÃO', 'LOCION'],
                'tipo': 'lotion'
            },
            'shampoo': {
                'palavras': ['SHAMPOO'],
                'tipo': 'shampoo'
            },
            'shot': {
                'palavras': ['SHOT'],
                'tipo': 'shot'
            },
            'ovulo': {
                'palavras': ['ÓVULO', 'OVULO'],
                'tipo': 'ovulo'
            },
            'comprimido_sublingual': {
                'palavras': ['SUBLINGUAL'],
                'tipo': 'comprimido_sublingual'
            },
            'capsula_oleosa': {
                'palavras': ['OLEOSA', 'OLEOSO'],
                'tipo': 'capsula_oleosa'
            },
            'goma': {
                'palavras': ['GOMA', 'GUMMY'],
                'tipo': 'goma'
            },
            'chocolate': {
                'palavras': ['CHOCOLATE'],
                'tipo': 'chocolate'
            },
            'filme': {
                'palavras': ['FILME', 'FILME SOLÚVEL'],
                'tipo': 'filme'
            },
        }
        
        # Adicionar tipos customizados que foram encontrados
        tipos_customizados = {
            'gel': {
                'palavras': ['GEL:'],
                'tipo': 'creme'  # GEL mapeia para CREME
            },
            'pastilha': {
                'palavras': ['PASTILHA MEDICAMENTOSA'],
                'tipo': 'comprimido_sublingual'  # PASTILHA mapeia para COMPRIMIDO SUBLINGUAL
            },
        }
        
        # Verificar padrões customizados primeiro (precedência)
        for chave, padrão in tipos_customizados.items():
            for palavra in padrão['palavras']:
                if palavra in descricao_upper:
                    try:
                        tipo_obj = TipoProduto.objects.filter(
                            tipo=padrão['tipo'],
                            ativo=True
                        ).first()
                        return tipo_obj, padrão['tipo']
                    except:
                        return None, padrão['tipo']
        
        # Verificar cada padrão normal
        for chave, padrão in padroes.items():
            for palavra in padrão['palavras']:
                if palavra in descricao_upper:
                    try:
                        tipo_obj = TipoProduto.objects.filter(
                            tipo=padrão['tipo'],
                            ativo=True
                        ).first()
                        return tipo_obj, padrão['tipo']
                    except:
                        return None, padrão['tipo']
        
        return None, 'desconhecido'
    
    def obter_etapa_por_status(self, id_status):
        """
        Obtém a etapa baseada no IDSTATUSITEMPEDIDO
        """
        grupo = self.STATUS_ETAPA_MAP.get(id_status)
        
        if not grupo:
            # Se não encontrar mapeamento, retorna a primeira etapa
            return Etapa.objects.filter(ativa=True).order_by('sequencia').first()
        
        return Etapa.objects.filter(
            grupo=grupo,
            ativa=True
        ).order_by('sequencia').first()
    
    def handle(self, *args, **kwargs):
        pagina = kwargs.get('pagina', 1)
        tamanho = kwargs.get('tamanho', 50)
        
        # URL da API
        url = f"https://b61b2bc163ff.ngrok-free.app/tabelas/FC0M100?pagina={pagina}&tamanho={tamanho}"
        
        try:
            self.stdout.write(f"🔄 Sincronizando pedidos da página {pagina}...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            dados = response.json()
            pedidos_data = dados.get('dados', [])
            
            if not pedidos_data:
                self.stdout.write(self.style.WARNING(f'Nenhum pedido encontrado na página {pagina}'))
                return
            
            criados = 0
            atualizados = 0
            duplicados = 0
            erros = 0
            
            for item in pedidos_data:
                try:
                    id_api = item.get('ID')
                    id_pedido = item.get('IDPEDIDO')
                    id_pedido_web = item.get('IDPEDIDOWEB')
                    descricao = item.get('DESCRICAOWEB', '')
                    quantidade = item.get('QUANT', 1)
                    pruni = item.get('PRUNI')
                    vrtot = item.get('VRTOT')
                    dtalt = item.get('DTALT')
                    hralt = item.get('HRALT')
                    id_status = item.get('IDSTATUSITEMPEDIDO', 1)
                    nrorc = item.get('NRORC')
                    
                    # Extrair quantidade de cápsulas/sachês da descrição se houver
                    quantidade_extraida = self.extrair_quantidade_produto(descricao)
                    if quantidade_extraida:
                        quantidade = quantidade_extraida
                    
                    # Validar ID único
                    if not id_api:
                        erros += 1
                        self.stdout.write(self.style.WARNING(f'Item sem ID, pulando...'))
                        continue
                    
                    # Criar código único com os IDs da API
                    codigo_pedido = f"API-{id_api}-{id_pedido}-{id_pedido_web}"
                    
                    # Converter data e hora
                    data_atualizacao = None
                    datetime_atualizacao = None
                    if dtalt and dtalt != '0001-01-01':
                        try:
                            data_atualizacao = datetime.strptime(dtalt, '%Y-%m-%d').date()
                            if hralt and hralt != '00:00:00':
                                datetime_atualizacao = datetime.strptime(f"{dtalt} {hralt}", '%Y-%m-%d %H:%M:%S')
                            else:
                                datetime_atualizacao = datetime.strptime(dtalt, '%Y-%m-%d')
                        except Exception as date_err:
                            self.stdout.write(self.style.WARNING(f'Erro ao converter data {dtalt}: {date_err}'))
                    
                    # Extrair tipo de produto da descrição
                    tipo_produto, tipo_identificado = self.extrair_tipo_produto(descricao)
                    
                    # Obter etapa correta
                    etapa_atual = self.obter_etapa_por_status(id_status)
                    if not etapa_atual:
                        etapa_atual = Etapa.objects.filter(ativa=True).order_by('sequencia').first()
                        if not etapa_atual:
                            self.stdout.write(self.style.ERROR('Nenhuma etapa ativa encontrada!'))
                            erros += 1
                            continue
                    
                    # Verificar se já existe
                    pedido_existe = Pedido.objects.filter(id_api=id_api).exists()
                    
                    if pedido_existe:
                        # Atualizar pedido existente
                        pedido = Pedido.objects.get(id_api=id_api)
                        pedido.id_pedido_api = id_pedido
                        pedido.id_pedido_web = id_pedido_web
                        pedido.descricao_web = descricao
                        pedido.quantidade = quantidade
                        pedido.price_unit = Decimal(str(pruni)) if pruni else None
                        pedido.price_total = Decimal(str(vrtot)) if vrtot else None
                        pedido.data_atualizacao_api = data_atualizacao
                        pedido.tipo_identificado = tipo_identificado
                        if datetime_atualizacao:
                            pedido.atualizado_em = datetime_atualizacao
                        if tipo_produto:
                            pedido.tipo = tipo_produto
                        pedido.etapa_atual = etapa_atual
                        pedido.save()
                        atualizados += 1
                    else:
                        # Criar novo pedido
                        pedido = Pedido.objects.create(
                            id_api=id_api,
                            codigo_pedido=codigo_pedido,
                            nome=descricao[:200] if descricao else f'Pedido {id_api}',
                            quantidade=quantidade,
                            id_pedido_api=id_pedido,
                            id_pedido_web=id_pedido_web,
                            descricao_web=descricao,
                            price_unit=Decimal(str(pruni)) if pruni else None,
                            price_total=Decimal(str(vrtot)) if vrtot else None,
                            data_atualizacao_api=data_atualizacao,
                            tipo_identificado=tipo_identificado,
                            tipo=tipo_produto,
                            etapa_atual=etapa_atual,
                            status='em_fluxo',
                        )
                        # Atualizar timestamp se fornecido
                        if datetime_atualizacao:
                            pedido.criado_em = datetime_atualizacao
                            pedido.save()
                        criados += 1
                        
                except IntegrityError as e:
                    duplicados += 1
                    self.stdout.write(self.style.WARNING(f'Registro duplicado ID {id_api}: {str(e)[:80]}'))
                except Exception as e:
                    erros += 1
                    self.stdout.write(self.style.WARNING(f'Erro ao processar item ID {id_api}: {str(e)[:100]}'))
            
            # Resumo
            self.stdout.write(self.style.SUCCESS(f'\n✅ Sincronização concluída!'))
            self.stdout.write(f'   📝 Criados: {criados}')
            self.stdout.write(f'   🔄 Atualizados: {atualizados}')
            if duplicados > 0:
                self.stdout.write(self.style.WARNING(f'   ⚠️  Duplicados: {duplicados}'))
            if erros > 0:
                self.stdout.write(self.style.WARNING(f'   ❌ Erros: {erros}'))
            
            total_pedidos = Pedido.objects.count()
            self.stdout.write(f'   📊 Total de pedidos no banco: {total_pedidos}')
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Erro ao conectar com a API: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro inesperado: {str(e)}'))
