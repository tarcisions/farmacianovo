from django.core.management.base import BaseCommand
from django.core.management import call_command
import time


class Command(BaseCommand):
    help = 'Sincroniza dados históricos de múltiplas páginas (útil para carga inicial)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--total-paginas',
            type=int,
            default=10,
            help='Total de páginas para sincronizar (padrão: 10 = ~500 registros)'
        )
        parser.add_argument(
            '--tamanho-pagina',
            type=int,
            default=50,
            help='Registros por página (padrão: 50)'
        )
        parser.add_argument(
            '--intervalo',
            type=float,
            default=1,
            help='Intervalo em segundos entre requisições (padrão: 1s)'
        )
    
    def handle(self, *args, **kwargs):
        total_paginas = kwargs.get('total_paginas', 10)
        tamanho_pagina = kwargs.get('tamanho_pagina', 50)
        intervalo = kwargs.get('intervalo', 1)
        
        self.stdout.write(self.style.SUCCESS(f'\n🔄 Sincronizando {total_paginas} páginas de histórico...\n'))
        
        total_criados = 0
        total_atualizados = 0
        total_erros = 0
        
        for pagina in range(1, total_paginas + 1):
            self.stdout.write(f'Página {pagina}/{total_paginas}... ', ending='')
            
            try:
                call_command(
                    'sincronizar_api_pedidos',
                    pagina=pagina,
                    tamanho=tamanho_pagina,
                    verbosity=0
                )
                self.stdout.write(self.style.SUCCESS('✓'))
                
                # Aguardar intervalo para não sobrecarregar API
                if pagina < total_paginas:
                    time.sleep(intervalo)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Erro: {str(e)[:50]}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Sincronização histórica concluída!'))
