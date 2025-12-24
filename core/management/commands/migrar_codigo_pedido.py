from django.core.management.base import BaseCommand
from core.models import Pedido


class Command(BaseCommand):
    help = 'Atualiza código_pedido para o novo formato com NRORC'
    
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('\n🔄 Atualizando formato de código_pedido...\n'))
        
        pedidos = Pedido.objects.filter(nrorc__isnull=False).order_by('-nrorc')
        total = pedidos.count()
        atualizados = 0
        
        for pedido in pedidos:
            novo_codigo = f"NRORC_{pedido.nrorc}"
            
            if pedido.codigo_pedido != novo_codigo:
                self.stdout.write(f"ID {pedido.nrorc}: {pedido.codigo_pedido} → {novo_codigo}")
                pedido.codigo_pedido = novo_codigo
                pedido.save()
                atualizados += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Atualização concluída!'))
        self.stdout.write(f'   📝 Atualizados: {atualizados}')
        self.stdout.write(f'   📊 Total de pedidos: {total}\n')
