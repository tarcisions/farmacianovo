"""
Scheduler para sincronização automática da API
Chama a API em intervalos configuráveis sem usar Celery
"""

import logging
import requests
import re
from datetime import datetime
from decimal import Decimal
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django.db import IntegrityError
from core.models import Pedido, Etapa, TipoProduto

logger = logging.getLogger(__name__)


def extrair_tipo_produto(descricao_web):
    """Extrai o tipo de produto da descrição"""
    if not descricao_web:
        return None, 'desconhecido'
    
    descricao_upper = descricao_web.upper()
    
    padroes = {
        'capsula': ['CAPSULA', 'CAP'],
        'sache': ['SACHE', 'SACHÊ', 'ENVELOPE'],
        'liquido_pediatrico': ['ML', 'LIQUIDO', 'LÍQUIDO', 'XAROPE', 'TCM LIQUIDO'],
        'creme': ['CREME', 'POMADA', 'PENTRAVAN', 'GEL'],
        'lotion': ['LOÇÃO', 'LOCION'],
        'shampoo': ['SHAMPOO'],
        'shot': ['SHOT'],
        'ovulo': ['ÓVULO', 'OVULO'],
        'comprimido_sublingual': ['SUBLINGUAL', 'PASTILHA'],
        'capsula_oleosa': ['OLEOSA', 'OLEOSO'],
        'goma': ['GOMA', 'GUMMY'],
        'chocolate': ['CHOCOLATE'],
        'filme': ['FILME'],
    }
    
    for tipo_chave, palavras in padroes.items():
        for palavra in palavras:
            if palavra in descricao_upper:
                try:
                    tipo_obj = TipoProduto.objects.get(tipo=tipo_chave)
                    return tipo_obj, tipo_chave
                except TipoProduto.DoesNotExist:
                    return None, tipo_chave
    
    return None, 'desconhecido'


def extrair_quantidade_produto(descricao_web):
    """
    Extrai a quantidade de unidades do produto APENAS de CAPSULA e ENVELOPE
    Busca pelos padrões: "CAPSULA: XXcap" ou "ENVELOPE: XXenv"
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


def processar_e_salvar_pedidos(dados_api):
    """Processa dados da API e salva no banco de dados - apenas atualiza se houve mudanças"""
    if not dados_api or 'dados' not in dados_api:
        return {'criados': 0, 'atualizados': 0, 'sem_mudancas': 0, 'erros': 0}
    
    criados = 0
    atualizados = 0
    sem_mudancas = 0
    erros = 0
    
    try:
        # Obter etapa padrão (triagem)
        etapa_atual = Etapa.objects.filter(grupo='triagem').first()
        if not etapa_atual:
            etapa_atual = Etapa.objects.first()
    except:
        etapa_atual = None
    
    for item in dados_api.get('dados', []):
        try:
            id_api = item.get('ID')
            id_pedido = item.get('IDPEDIDO')
            id_pedido_web = item.get('IDPEDIDOWEB')
            descricao = item.get('DESCRICAOWEB', '')
            quantidade = item.get('QUANT', 0)
            pruni = item.get('PRUNI')
            vrtot = item.get('VRTOT')
            dtalt = item.get('DTALT')
            hralt = item.get('HRALT')
            
            # Tentar extrair quantidade da descrição (cápsulas/envelopes)
            quantidade_extraida = extrair_quantidade_produto(descricao)
            if quantidade_extraida is not None:
                quantidade = quantidade_extraida
            
            # Gerar código do pedido
            codigo_pedido = f'API_{id_api}_{id_pedido_web}' if id_api else f'WEB_{id_pedido_web}'
            
            # Extrair tipo de produto
            tipo_produto, tipo_identificado = extrair_tipo_produto(descricao)
            
            # Verificar se já existe
            pedido_existente = Pedido.objects.filter(id_api=id_api).first()
            
            if pedido_existente:
                # Verificar se houve mudanças
                houve_mudanca = False
                
                # Preparar valores para comparação
                novo_nome = descricao[:200] if descricao else f'Pedido {id_api}'
                novo_price_unit = Decimal(str(pruni)) if pruni else None
                novo_price_total = Decimal(str(vrtot)) if vrtot else None
                
                # Comparar cada campo individualmente
                if pedido_existente.nome != novo_nome:
                    houve_mudanca = True
                elif pedido_existente.quantidade != quantidade:
                    houve_mudanca = True
                elif pedido_existente.descricao_web != descricao:
                    houve_mudanca = True
                elif pedido_existente.price_unit != novo_price_unit:
                    houve_mudanca = True
                elif pedido_existente.price_total != novo_price_total:
                    houve_mudanca = True
                elif pedido_existente.tipo_identificado != tipo_identificado:
                    houve_mudanca = True
                elif dtalt and str(pedido_existente.data_atualizacao_api) != str(dtalt):
                    houve_mudanca = True
                elif hralt and str(pedido_existente.hora_atualizacao_api) != str(hralt):
                    houve_mudanca = True
                elif tipo_produto and pedido_existente.tipo != tipo_produto:
                    houve_mudanca = True
                
                if houve_mudanca:
                    # Atualizar apenas se houve mudança
                    pedido_existente.nome = novo_nome
                    pedido_existente.quantidade = quantidade
                    pedido_existente.descricao_web = descricao
                    pedido_existente.price_unit = novo_price_unit
                    pedido_existente.price_total = novo_price_total
                    pedido_existente.tipo_identificado = tipo_identificado
                    if dtalt:
                        pedido_existente.data_atualizacao_api = dtalt
                    if hralt:
                        pedido_existente.hora_atualizacao_api = hralt
                    if tipo_produto:
                        pedido_existente.tipo = tipo_produto
                    pedido_existente.save()
                    atualizados += 1
                else:
                    # Nenhuma mudança detectada
                    sem_mudancas += 1
                
            else:
                # Criar novo
                Pedido.objects.create(
                    id_api=id_api,
                    codigo_pedido=codigo_pedido,
                    nome=descricao[:200] if descricao else f'Pedido {id_api}',
                    quantidade=quantidade,
                    id_pedido_api=id_pedido,
                    id_pedido_web=id_pedido_web,
                    descricao_web=descricao,
                    price_unit=Decimal(str(pruni)) if pruni else None,
                    price_total=Decimal(str(vrtot)) if vrtot else None,
                    data_atualizacao_api=dtalt if dtalt else None,
                    hora_atualizacao_api=hralt if hralt else None,
                    tipo_identificado=tipo_identificado,
                    tipo=tipo_produto,
                    etapa_atual=etapa_atual,
                    status='em_fluxo',
                )
                criados += 1
                
        except IntegrityError as e:
            logger.warning(f'Registro duplicado ID {id_api}: {str(e)[:80]}')
            erros += 1
        except Exception as e:
            logger.error(f'Erro ao processar item ID {item.get("ID")}: {str(e)}')
            erros += 1
    
    logger.info(f'[PROCESSAMENTO] Pedidos: {criados} criados, {atualizados} atualizados, {sem_mudancas} sem mudanças, {erros} erros')
    return {'criados': criados, 'atualizados': atualizados, 'sem_mudancas': sem_mudancas, 'erros': erros}


logger = logging.getLogger(__name__)


class SincronizadorAPI:
    """Gerencia a sincronização automática da API"""
    
    # Configurações padrão - EDITE AQUI para customizar
    CONFIG = {
        'url_base': 'https://b61b2bc163ff.ngrok-free.app/tabelas/FC0M100',
        'intervalo_minutos': 3000,  # Mude a URL acima e depois reinicie
        'paginacoes': [
            {'pagina': 1, 'tamanho': 50},
            # Adicione mais paginações aqui se quiser
            # {'pagina': 2, 'tamanho': 50},
            # {'pagina': 3, 'tamanho': 50},
        ],
        'timeout': 30,
        'ativo': True,
    }
    
    @staticmethod
    def chamar_api(pagina, tamanho):
        """Faz a chamada HTTP para a API e processa os dados"""
        try:
            url = f"{SincronizadorAPI.CONFIG['url_base']}?pagina={pagina}&tamanho={tamanho}"
            
            response = requests.get(
                url,
                timeout=SincronizadorAPI.CONFIG['timeout']
            )
            response.raise_for_status()
            
            dados = response.json()
            logger.info(f"[OK] API chamada com sucesso - Página {pagina}, Tamanho {tamanho}")
            
            # Processar e salvar os pedidos
            resultado_processamento = processar_e_salvar_pedidos(dados)
            
            logger.debug(f"Dados recebidos: {len(dados.get('dados', []))} itens")
            
            return {
                'sucesso': True,
                'status': response.status_code,
                'items_recebidos': len(dados.get('dados', [])),
                'processamento': resultado_processamento,
                'timestamp': datetime.now().isoformat()
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"[ERRO] Timeout na chamada da API (página {pagina})")
            return {'sucesso': False, 'erro': 'Timeout', 'pagina': pagina}
        except requests.exceptions.ConnectionError:
            logger.error(f"[ERRO] Erro de conexão com a API (página {pagina})")
            return {'sucesso': False, 'erro': 'Conexão recusada', 'pagina': pagina}
        except requests.exceptions.RequestException as e:
            logger.error(f"[ERRO] Erro na requisição (página {pagina}): {str(e)}")
            return {'sucesso': False, 'erro': str(e), 'pagina': pagina}
        except Exception as e:
            logger.error(f"[ERRO] Erro inesperado (página {pagina}): {str(e)}")
            return {'sucesso': False, 'erro': str(e), 'pagina': pagina}
    
    @staticmethod
    def sincronizar():
        """Executa a sincronização de todas as paginações configuradas"""
        if not SincronizadorAPI.CONFIG['ativo']:
            logger.info("Sincronizador está desativado")
            return
        
        logger.info(f"\n{'='*60}")
        logger.info(f"SINCRONIZAÇÃO INICIADA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*60}")
        
        resultados = []
        for paginacao in SincronizadorAPI.CONFIG['paginacoes']:
            resultado = SincronizadorAPI.chamar_api(
                paginacao['pagina'],
                paginacao['tamanho']
            )
            resultados.append(resultado)
        
        logger.info(f"[FINALIZADO] Sincronização com {len(resultados)} chamada(s)")
        logger.info(f"{'='*60}")
        
        return resultados


class AgendadorSincronizacao:
    """Gerencia o scheduler de background"""
    
    scheduler = None
    
    @classmethod
    def iniciar(cls):
        """Inicia o scheduler de background"""
        if cls.scheduler is not None and cls.scheduler.running:
            logger.warning("Scheduler já está em execução")
            return
        
        try:
            cls.scheduler = BackgroundScheduler(daemon=True)
            
            # Adiciona o job de sincronização
            intervalo = SincronizadorAPI.CONFIG['intervalo_minutos']
            cls.scheduler.add_job(
                SincronizadorAPI.sincronizar,
                'interval',
                minutes=intervalo,
                id='sincronizacao_api',
                name='Sincronização automática da API',
                replace_existing=True,
                max_instances=1,  # Evita múltiplas instâncias rodando
            )
            
            cls.scheduler.start()
            logger.info(f"[INICIADO] Scheduler rodando! Sincronização a cada {intervalo} minuto(s)")
            
        except Exception as e:
            logger.error(f"[ERRO] Falha ao iniciar scheduler: {str(e)}")
    
    @classmethod
    def parar(cls):
        """Para o scheduler"""
        if cls.scheduler and cls.scheduler.running:
            cls.scheduler.shutdown()
            logger.info("[PARADO] Scheduler encerrado")
    
    @classmethod
    def sincronizar_agora(cls):
        """Força uma sincronização imediata"""
        logger.info("Sincronização manual solicitada...")
        SincronizadorAPI.sincronizar()
    
    @classmethod
    def obter_status(cls):
        """Retorna o status do scheduler"""
        if cls.scheduler is None:
            return {'ativo': False, 'jobs': []}
        
        if cls.scheduler.running:
            jobs = [
                {
                    'id': job.id,
                    'nome': job.name,
                    'proxima_execucao': str(job.next_run_time),
                    'intervalo': f"{job.trigger.interval.total_seconds()/60:.0f} minuto(s)"
                }
                for job in cls.scheduler.get_jobs()
            ]
            return {'ativo': True, 'jobs': jobs}
        
        return {'ativo': False, 'jobs': []}
