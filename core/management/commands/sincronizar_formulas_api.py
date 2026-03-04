"""
Sincronizador de API reformulado para o novo fluxo com PedidoMestre e FormulaItem
Agrupa pedidos por NRORC ao invés de criar um Pedido por item
"""

import logging
import requests
import re
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone
from core.models import (
    PedidoMestre, FormulaItem, Etapa, TipoProduto,
    ConfiguracaoAPI, AgendamentoSincronizacao
)
from core.api_sync_helpers import sincronizar_datetime_api

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


def extrair_volume(descricao_web):
    """Extrai o volume em ML da descrição"""
    if not descricao_web:
        return None
    
    # Busca padrões como "10ML", "60 ML", etc
    match = re.search(r'(\d+)\s*ML', descricao_web.upper())
    if match:
        return f"{match.group(1)}ML"
    
    return None


class Command(BaseCommand):
    help = 'Sincroniza pedidos da API (novo fluxo com FormulaItem)'
    
    def add_arguments(self, parser):
        parser.add_argument('--api_id', type=int, help='ID da API a sincronizar (se não informado, usa todas ativas)')
        parser.add_argument('--pagina', type=int, default=1, help='Página inicial')
        parser.add_argument('--tamanho', type=int, default=50, help='Tamanho da página')
    
    def handle(self, *args, **options):
        try:
            api_id = options.get('api_id')
            pagina_inicial = options.get('pagina', 1)
            tamanho_pagina = options.get('tamanho', 50)
            
            # Obter API(s)
            if api_id:
                apis = ConfiguracaoAPI.objects.filter(id=api_id, ativa=True)
            else:
                apis = ConfiguracaoAPI.objects.filter(ativa=True)
            
            if not apis.exists():
                self.stdout.write(self.style.WARNING('Nenhuma API ativa encontrada'))
                return
            
            total_criados = 0
            total_atualizados = 0
            total_erros = 0
            
            for api in apis:
                resultado = self.sincronizar_api(api, pagina_inicial, tamanho_pagina)
                total_criados += resultado['criados']
                total_atualizados += resultado['atualizados']
                total_erros += resultado['erros']
                
                self.stdout.write(self.style.SUCCESS(f'\n[OK] Sincronização de {api.nome} concluída!'))
                self.stdout.write(f'   Pedidos Mestres criados: {resultado["pedidos_mestres_criados"]}')
                self.stdout.write(f'   Formulas criadas: {resultado["formulas_criadas"]}')
                self.stdout.write(f'   Formulas atualizadas: {total_atualizados}')
                if total_erros > 0:
                    self.stdout.write(self.style.WARNING(f'   Erros: {total_erros}'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro geral: {str(e)}'))
    
    def sincronizar_api(self, api, pagina, tamanho):
        """Sincroniza uma API específica"""
        resultado = {
            'criados': 0,
            'atualizados': 0,
            'erros': 0,
            'pedidos_mestres_criados': 0,
            'formulas_criadas': 0,
        }
        
        try:
            url = f"{api.url_base}?pagina={pagina}&tamanho={tamanho}"
            headers = api.obter_headers_requisicao()
            
            self.stdout.write(f'Sincronizando {api.nome} ({url})...')
            
            response = requests.get(url, headers=headers, timeout=api.timeout)
            response.raise_for_status()
            
            dados = response.json()
            pedidos_data = dados.get('dados', [])
            
            if not pedidos_data:
                self.stdout.write(self.style.WARNING('Nenhum pedido encontrado na API'))
                return resultado
            
            # Agrupar dados por NRORC
            pedidos_por_nrorc = {}
            for item in pedidos_data:
                nrorc = item.get('NRORC')
                if nrorc:
                    if nrorc not in pedidos_por_nrorc:
                        pedidos_por_nrorc[nrorc] = []
                    pedidos_por_nrorc[nrorc].append(item)
            
            # Processar cada NRORC (que é um PedidoMestre com N FormulaItems)
            for nrorc, items_formula in pedidos_por_nrorc.items():
                try:
                    with transaction.atomic():
                        # Obter ou criar PedidoMestre
                        pedido_mestre, created = PedidoMestre.objects.get_or_create(
                            nrorc=nrorc,
                            defaults={'status': 'em_processamento'}
                        )
                        
                        if created:
                            resultado['pedidos_mestres_criados'] += 1
                        
                        # Processar cada fórmula deste pedido
                        for item in items_formula:
                            try:
                                id_api = item.get('ID')
                                descricao = item.get('DESCRICAOWEB', '')
                                quantidade = item.get('QUANT', 1)
                                serieo = item.get('SERIEO', '')
                                pruni = item.get('PRUNI')
                                vrtot = item.get('VRTOT')
                                dtalt = item.get('DTALT')
                                hralt = item.get('HRALT')
                                
                                if not id_api:
                                    continue  # Pular item sem ID
                                
                                # Extrair volume
                                volume_ml = extrair_volume(descricao)
                                
                                # Extrair tipo de produto
                                tipo_produto, tipo_identificado = extrair_tipo_produto(descricao)
                                
                                # Obter etapa inicial (triagem)
                                etapa_inicial = Etapa.objects.filter(
                                    sequencia=1, ativa=True
                                ).first()
                                
                                if not etapa_inicial:
                                    etapa_inicial = Etapa.objects.filter(ativa=True).order_by('sequencia').first()
                                
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
                                
                                # Sincronizar datetime da API (DTALT + HRALT)
                                if dtalt or hralt:
                                    sincronizar_datetime_api(formula, dtalt, hralt)
                                
                                if formula_created:
                                    resultado['formulas_criadas'] += 1
                                else:
                                    # Atualizar fórmula existente
                                    formula.descricao = descricao[:200] if descricao else formula.descricao
                                    formula.quantidade = quantidade
                                    formula.price_unit = Decimal(str(pruni)) if pruni else formula.price_unit
                                    formula.price_total = Decimal(str(vrtot)) if vrtot else formula.price_total
                                    formula.save()
                                    resultado['atualizados'] += 1
                                
                                resultado['criados'] += 1
                            
                            except Exception as e:
                                resultado['erros'] += 1
                                logger.warning(f'Erro ao processar fórmula {id_api}: {str(e)}')
                
                except Exception as e:
                    resultado['erros'] += 1
                    logger.warning(f'Erro ao processar NRORC {nrorc}: {str(e)}')
        
        except Exception as e:
            resultado['erros'] += 1
            logger.error(f'Erro ao sincronizar API {api.nome}: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Erro: {str(e)}'))
        
        return resultado
