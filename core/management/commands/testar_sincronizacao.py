from django.core.management.base import BaseCommand
from core.models import Pedido, Etapa
from decimal import Decimal
from datetime import datetime
import json


class Command(BaseCommand):
    help = 'Testa a sincronização com dados simulados'
    
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('\n🧪 Teste de Sincronização com Dados Simulados\n'))
        
        # Dados de exemplo
        dados_teste = [
            {
                "ID": 86748,
                "IDPEDIDO": 45070,
                "IDPEDIDOWEB": 188440403,
                "DESCRICAOWEB": "FORMULA MANIPULADA - OUTRAS: 90ML | VITAMINA D3 GOTAS 1200 ui; VITAMINA A OLEOSA 6500 ui; VITAMINA K2MK7 OLEOSA 20 mcg; ALFATOCOFEROL OLEOSO 50 mg; TCM LIQUIDO 1 ml",
                "IDSTATUSITEMPEDIDO": 1,
                "QUANT": 1,
                "PRUNI": 161.0,
                "VRTOT": 161.0,
                "DTALT": "2025-08-06",
                "HRALT": "08:31:46",
                "NRORC": 60159,
            },
            {
                "ID": 86747,
                "IDPEDIDO": 45046,
                "IDPEDIDOWEB": 188432662,
                "DESCRICAOWEB": "FORMULA MANIPULADA - CAPSULA: 180CAP | DAPAGLIFOZINA 10 mg",
                "IDSTATUSITEMPEDIDO": 2,
                "QUANT": 2,
                "PRUNI": 75.0,
                "VRTOT": 150.0,
                "DTALT": "2025-08-05",
                "HRALT": "14:22:30",
                "NRORC": 60158,
            },
            {
                "ID": 86746,
                "IDPEDIDO": 45046,
                "IDPEDIDOWEB": 188432662,
                "DESCRICAOWEB": "FORMULA MANIPULADA - OUTRAS: 40G | CLINDAMICINA 2 %; PENTRAVAN 1 g",
                "IDSTATUSITEMPEDIDO": 1,
                "QUANT": 1,
                "PRUNI": 85.0,
                "VRTOT": 85.0,
                "DTALT": "2025-08-04",
                "HRALT": "09:15:00",
                "NRORC": 60157,
            },
        ]
        
        # Importar o comando real para usar as funções
        from core.management.commands.sincronizar_api_pedidos import Command as SincCommand
        sinc_cmd = SincCommand()
        
        primeira_etapa = Etapa.objects.filter(ativa=True).order_by('sequencia').first()
        if not primeira_etapa:
            self.stdout.write(self.style.ERROR('❌ Nenhuma etapa ativa encontrada!'))
            return
        
        criados = 0
        atualizados = 0
        
        for item in dados_teste:
            self.stdout.write(f"\n📦 Processando ID {item['ID']}...")
            
            # Extrair tipo
            tipo_produto, tipo_identificado = sinc_cmd.extrair_tipo_produto(item['DESCRICAOWEB'])
            self.stdout.write(f"   Tipo identificado: {tipo_identificado}")
            
            # Obter etapa
            etapa = sinc_cmd.obter_etapa_por_status(item['IDSTATUSITEMPEDIDO'])
            self.stdout.write(f"   Etapa: {etapa.nome if etapa else 'N/A'}")
            
            # Processar data
            dtalt = item.get('DTALT')
            hralt = item.get('HRALT')
            datetime_atualizacao = None
            if dtalt and dtalt != '0001-01-01':
                try:
                    if hralt and hralt != '00:00:00':
                        datetime_atualizacao = datetime.strptime(f"{dtalt} {hralt}", '%Y-%m-%d %H:%M:%S')
                    else:
                        datetime_atualizacao = datetime.strptime(dtalt, '%Y-%m-%d')
                    self.stdout.write(f"   Data/Hora: {datetime_atualizacao}")
                except Exception as e:
                    self.stdout.write(f"   ⚠️  Erro ao converter data: {e}")
            
            # Criar/Atualizar
            codigo_pedido = f"API-{item['ID']}-{item['IDPEDIDO']}-{item['IDPEDIDOWEB']}"
            descricao = item['DESCRICAOWEB']
            
            pedido_existe = Pedido.objects.filter(id_api=item['ID']).exists()
            
            if not pedido_existe:
                try:
                    pedido = Pedido.objects.create(
                        id_api=item['ID'],
                        codigo_pedido=codigo_pedido,
                        nome=descricao[:200],
                        quantidade=item['QUANT'],
                        id_pedido_api=item['IDPEDIDO'],
                        id_pedido_web=item['IDPEDIDOWEB'],
                        descricao_web=descricao,
                        price_unit=Decimal(str(item['PRUNI'])),
                        price_total=Decimal(str(item['VRTOT'])),
                        data_atualizacao_api=datetime.strptime(dtalt, '%Y-%m-%d').date() if dtalt != '0001-01-01' else None,
                        tipo_identificado=tipo_identificado,
                        tipo=tipo_produto,
                        etapa_atual=etapa,
                        status='em_fluxo',
                    )
                    if datetime_atualizacao:
                        pedido.criado_em = datetime_atualizacao
                        pedido.save()
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Pedido criado: {pedido.codigo_pedido}"))
                    criados += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Erro: {str(e)[:100]}"))
            else:
                self.stdout.write(f"   ℹ️  Pedido já existe (ID {item['ID']})")
                atualizados += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n\n✅ Teste concluído!'))
        self.stdout.write(f'   📝 Criados: {criados}')
        self.stdout.write(f'   🔄 Atualizados: {atualizados}')
        
        total = Pedido.objects.count()
        self.stdout.write(f'   📊 Total no banco: {total}')
        
        # Mostrar pedidos criados
        self.stdout.write(self.style.WARNING(f'\n📋 Pedidos na base de dados:\n'))
        pedidos = Pedido.objects.all().order_by('-id_api')[:10]
        for p in pedidos:
            self.stdout.write(f'   - {p.codigo_pedido} | Tipo: {p.tipo_identificado} | Etapa: {p.etapa_atual.nome if p.etapa_atual else "N/A"}')
