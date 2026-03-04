"""
Scheduler para sincronização automática da API
Chama a API em intervalos configuráveis sem usar Celery
"""

import logging
import requests
import re
from datetime import datetime, time
from decimal import Decimal
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from django.core.management import call_command
from core.models import PedidoMestre, FormulaItem, Etapa, TipoProduto, ConfiguracaoAPI, AgendamentoSincronizacao

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
    """
    Processa dados da API e salva no banco usando PedidoMestre e FormulaItem
    Agrupa por NRORC: cada NRORC = PedidoMestre, cada item diferente = FormulaItem
    """
    if not dados_api or 'dados' not in dados_api:
        return {'criados': 0, 'atualizados': 0, 'sem_mudancas': 0, 'erros': 0}
    
    criados = 0
    atualizados = 0
    sem_mudancas = 0
    erros = 0
    
    try:
        # Obter etapa padrão (triagem)
        etapa_inicial = Etapa.objects.filter(sequencia=1, ativa=True).first()
        if not etapa_inicial:
            etapa_inicial = Etapa.objects.filter(ativa=True).order_by('sequencia').first()
    except:
        etapa_inicial = None
    
    # Agrupar dados por NRORC
    pedidos_por_nrorc = {}
    for item in dados_api.get('dados', []):
        nrorc = item.get('NRORC')
        if nrorc:
            if nrorc not in pedidos_por_nrorc:
                pedidos_por_nrorc[nrorc] = []
            pedidos_por_nrorc[nrorc].append(item)
    
    # Processar cada grupo NRORC (cada um é um PedidoMestre)
    for nrorc, items in pedidos_por_nrorc.items():
        try:
            # Criar ou obter PedidoMestre
            pedido_mestre, pm_created = PedidoMestre.objects.get_or_create(
                nrorc=nrorc,
                defaults={'status': 'em_processamento'}
            )
            
            if pm_created:
                criados += 1
            
            # Processar cada fórmula (item) deste NRORC
            for item in items:
                try:
                    id_api = item.get('ID')
                    if not id_api:
                        continue
                    
                    descricao = item.get('DESCRICAOWEB', '')
                    quantidade = item.get('QUANT', 1)
                    serieo = item.get('SERIEO', '')
                    pruni = item.get('PRUNI')
                    vrtot = item.get('VRTOT')
                    dtalt = item.get('DTALT')
                    hralt = item.get('HRALT')
                    
                    # Extrair volume (ex: "10ML")
                    volume_ml = extrair_volume(descricao) if descricao else None
                    
                    # Extrair tipo de produto
                    tipo_produto, tipo_identificado = extrair_tipo_produto(descricao)
                    
                    # Obter ou criar FormulaItem
                    formula, formula_created = FormulaItem.objects.get_or_create(
                        id_api=str(id_api),
                        defaults={
                            'pedido_mestre': pedido_mestre,
                            'descricao': descricao[:200] if descricao else f'Formula {id_api}',
                            'quantidade': quantidade,
                            'volume_ml': volume_ml or '',
                            'serieo': serieo,
                            'price_unit': Decimal(str(pruni)) if pruni else None,
                            'price_total': Decimal(str(vrtot)) if vrtot else None,
                            'status': 'em_triagem',
                            'etapa_atual': etapa_inicial,
                        }
                    )
                    
                    if formula_created:
                        criados += 1
                    else:
                        # Verificar se houve mudanças
                        houve_mudanca = False
                        novo_descricao = descricao[:200] if descricao else formula.descricao
                        novo_price_unit = Decimal(str(pruni)) if pruni else None
                        novo_price_total = Decimal(str(vrtot)) if vrtot else None
                        
                        if formula.descricao != novo_descricao:
                            houve_mudanca = True
                        elif formula.quantidade != quantidade:
                            houve_mudanca = True
                        elif formula.price_unit != novo_price_unit:
                            houve_mudanca = True
                        elif formula.price_total != novo_price_total:
                            houve_mudanca = True
                        elif formula.serieo != serieo:
                            houve_mudanca = True
                        
                        if houve_mudanca:
                            formula.descricao = novo_descricao
                            formula.quantidade = quantidade
                            formula.volume_ml = volume_ml or formula.volume_ml
                            formula.serieo = serieo
                            formula.price_unit = novo_price_unit
                            formula.price_total = novo_price_total
                            formula.save()
                            atualizados += 1
                        else:
                            sem_mudancas += 1
                
                except IntegrityError as e:
                    logger.warning(f'Registro duplicado ID {id_api}: {str(e)[:80]}')
                    erros += 1
                except Exception as e:
                    logger.error(f'Erro ao processar formula {id_api}: {str(e)}')
                    erros += 1
        
        except Exception as e:
            logger.error(f'Erro ao processar NRORC {nrorc}: {str(e)}')
            erros += 1
    
    logger.info(f'[PROCESSAMENTO] Pedidos: {criados} criados, {atualizados} atualizados, {sem_mudancas} sem mudancas, {erros} erros')
    return {'criados': criados, 'atualizados': atualizados, 'sem_mudancas': sem_mudancas, 'erros': erros}


def extrair_volume(descricao):
    """Extrai o volume em ML da descrição (ex: '10ML' from 'VITAMINA A + TCM | 10ML')"""
    if not descricao:
        return None
    
    match = re.search(r'(\d+)\s*ML', descricao.upper())
    if match:
        return f"{match.group(1)}ML"
    
    return None


logger = logging.getLogger(__name__)


class SincronizadorAPI:
    """Gerencia a sincronização automática da API"""
    
    @staticmethod
    def chamar_api(api_config, pagina, tamanho):
        """Faz a chamada HTTP para a API e processa os dados"""
        try:
            url = f"{api_config.url_base}?pagina={pagina}&tamanho={tamanho}"
            
            # Obter headers de autenticação
            headers = api_config.obter_headers_requisicao()
            
            response = requests.get(
                url,
                timeout=api_config.timeout,
                headers=headers
            )
            response.raise_for_status()
            
            dados = response.json()
            logger.info(f"[OK] API '{api_config.nome}' chamada com sucesso - Página {pagina}, Tamanho {tamanho}")
            
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
            logger.error(f"[ERRO] Timeout na chamada da API '{api_config.nome}' (página {pagina})")
            return {'sucesso': False, 'erro': 'Timeout', 'pagina': pagina}
        except requests.exceptions.ConnectionError:
            logger.error(f"[ERRO] Erro de conexão com a API '{api_config.nome}' (página {pagina})")
            return {'sucesso': False, 'erro': 'Conexão recusada', 'pagina': pagina}
        except requests.exceptions.RequestException as e:
            logger.error(f"[ERRO] Erro na requisição '{api_config.nome}' (página {pagina}): {str(e)}")
            return {'sucesso': False, 'erro': str(e), 'pagina': pagina}
        except Exception as e:
            logger.error(f"[ERRO] Erro inesperado '{api_config.nome}' (página {pagina}): {str(e)}")
            return {'sucesso': False, 'erro': str(e), 'pagina': pagina}
    
    @staticmethod
    def sincronizar_agendamento(agendamento):
        """Executa a sincronização de um agendamento específico"""
        api_config = agendamento.api
        
        if not api_config.ativa or not agendamento.ativo:
            logger.info(f"Agendamento '{agendamento.nome}' está desativado")
            return
        
        logger.info(f"\n{'='*60}")
        logger.info(f"SINCRONIZAÇÃO: {agendamento.nome} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"API: {api_config.nome}")
        logger.info(f"{'='*60}")
        
        resultados = []
        paginacoes = agendamento.paginacoes if agendamento.paginacoes else [{'pagina': 1, 'tamanho': 50}]
        
        for paginacao in paginacoes:
            resultado = SincronizadorAPI.chamar_api(
                api_config,
                paginacao['pagina'],
                paginacao['tamanho']
            )
            resultados.append(resultado)
        
        logger.info(f"[FINALIZADO] Sincronização com {len(resultados)} chamada(s)")
        logger.info(f"{'='*60}")
        
        return resultados


class AgendadorSincronizacao:
    """Gerencia o scheduler de background baseado em agendamentos configuráveis"""
    
    scheduler = None
    
    @classmethod
    def iniciar(cls):
        """Inicia o scheduler de background com todos os agendamentos ativos"""
        if cls.scheduler is not None and cls.scheduler.running:
            logger.warning("Scheduler já está em execução")
            return
        
        try:
            cls.scheduler = BackgroundScheduler(daemon=True)
            
            # Buscar todos os agendamentos ativos
            agendamentos = AgendamentoSincronizacao.objects.filter(ativo=True)
            
            if not agendamentos.exists():
                logger.warning("[AVISO] Nenhum agendamento ativo encontrado!")
            
            for agendamento in agendamentos:
                cls.adicionar_job(agendamento)
            
            cls.scheduler.start()
            logger.info(f"[INICIADO] Scheduler rodando! {agendamentos.count()} agendamento(s) carregado(s)")
            
        except Exception as e:
            logger.error(f"[ERRO] Falha ao iniciar scheduler: {str(e)}")
    
    @classmethod
    def adicionar_job(cls, agendamento):
        """Adiciona um job para um agendamento específico"""
        try:
            horario = agendamento.horario_execucao
            
            if agendamento.executar_todos_os_dias:
                # Executar todos os dias no horário especificado
                cls.scheduler.add_job(
                    SincronizadorAPI.sincronizar_agendamento,
                    'cron',
                    hour=horario.hour,
                    minute=horario.minute,
                    second=0,
                    args=[agendamento],
                    id=f'agend_{agendamento.id}',
                    name=f'{agendamento.nome} (Todos os dias)',
                    replace_existing=True,
                    max_instances=1,
                )
                logger.info(f"[JOB] Agendado '{agendamento.nome}' para todos os dias às {horario.strftime('%H:%M')}")
            else:
                # Executar em dias específicos
                dias_semana_map = {
                    'segunda': 'mon',
                    'terca': 'tue',
                    'quarta': 'wed',
                    'quinta': 'thu',
                    'sexta': 'fri',
                    'sabado': 'sat',
                    'domingo': 'sun',
                }
                
                dias_cron = [dias_semana_map.get(d) for d in agendamento.dias_semana if d in dias_semana_map]
                
                if dias_cron:
                    cls.scheduler.add_job(
                        SincronizadorAPI.sincronizar_agendamento,
                        'cron',
                        day_of_week=','.join(dias_cron),
                        hour=horario.hour,
                        minute=horario.minute,
                        second=0,
                        args=[agendamento],
                        id=f'agend_{agendamento.id}',
                        name=f'{agendamento.nome} ({", ".join(agendamento.dias_semana)})',
                        replace_existing=True,
                        max_instances=1,
                    )
                    logger.info(f"[JOB] Agendado '{agendamento.nome}' para {', '.join(agendamento.dias_semana)} às {horario.strftime('%H:%M')}")
        except Exception as e:
            logger.error(f"[ERRO] Falha ao adicionar job para agendamento {agendamento.id}: {str(e)}")


    
    @classmethod
    def parar(cls):
        """Para o scheduler"""
        if cls.scheduler and cls.scheduler.running:
            cls.scheduler.shutdown()
            logger.info("[PARADO] Scheduler encerrado")
    
    @classmethod
    def sincronizar_agora(cls, agendamento_id=None):
        """Força uma sincronização imediata de um ou todos os agendamentos"""
        if agendamento_id:
            try:
                agendamento = AgendamentoSincronizacao.objects.get(id=agendamento_id)
                logger.info(f"Sincronização manual solicitada para '{agendamento.nome}'...")
                SincronizadorAPI.sincronizar_agendamento(agendamento)
            except AgendamentoSincronizacao.DoesNotExist:
                logger.error(f"Agendamento {agendamento_id} não encontrado")
        else:
            logger.info("Sincronização manual solicitada para todos os agendamentos...")
            for agendamento in AgendamentoSincronizacao.objects.filter(ativo=True):
                SincronizadorAPI.sincronizar_agendamento(agendamento)
    
    @classmethod
    def recarregar_agendamentos(cls):
        """Recarrega todos os agendamentos do banco de dados"""
        if cls.scheduler and cls.scheduler.running:
            cls.parar()
        cls.iniciar()
        logger.info("[RECARREGADO] Agendamentos recarregados do banco de dados")
    
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
                    'next_run_time': str(job.next_run_time),
                }
                for job in cls.scheduler.get_jobs()
            ]
            return {'ativo': True, 'jobs': jobs}
        
        return {'ativo': False, 'jobs': []}
