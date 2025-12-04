from django.core.management.base import BaseCommand
from core.models import Pedido
from core.management.commands.sincronizar_api_pedidos import Command as SincCommand


class Command(BaseCommand):
    help = 'Reidentifica tipos de todos os pedidos com tipo desconhecido'
    
    def handle(self, *args, **kwargs):
        sinc_cmd = SincCommand()
        
        self.stdout.write(self.style.WARNING('\n🔍 Reidentificando tipos de produtos...\n'))
        
        # Pegar pedidos desconhecidos
        pedidos_desconhecidos = Pedido.objects.filter(tipo_identificado='desconhecido')
        total = pedidos_desconhecidos.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ Todos os pedidos têm tipo identificado!'))
            return
        
        atualizados = 0
        ainda_desconhecidos = 0
        
        for pedido in pedidos_desconhecidos:
            if pedido.descricao_web:
                tipo_obj, tipo_id = sinc_cmd.extrair_tipo_produto(pedido.descricao_web)
                
                if tipo_id != 'desconhecido':
                    pedido.tipo_identificado = tipo_id
                    if tipo_obj:
                        pedido.tipo = tipo_obj
                    pedido.save()
                    atualizados += 1
                    self.stdout.write(f'✓ ID {pedido.id_api}: {tipo_id}')
                else:
                    ainda_desconhecidos += 1
                    self.stdout.write(self.style.WARNING(f'⚠️  ID {pedido.id_api}: ainda desconhecido'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Reidentificação concluída!'))
        self.stdout.write(f'   📝 Atualizados: {atualizados}')
        self.stdout.write(f'   ⚠️  Ainda desconhecidos: {ainda_desconhecidos}')
        self.stdout.write(f'   📊 Total processado: {total}\n')
