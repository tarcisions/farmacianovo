from django.core.management.base import BaseCommand
from core.models import FormulaItem
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Limpa tarefas ativas duplicadas, deixando apenas 1 por usuário'

    def handle(self, *args, **options):
        # Para cada usuário que tem fórmulas
        usuarios = User.objects.filter(formulas_assumidas__isnull=False).distinct()
        
        total_corrigidos = 0
        
        for usuario in usuarios:
            # Buscar todas as tarefas ativas deste usuário
            ativas = FormulaItem.objects.filter(
                funcionario_na_etapa=usuario,
                eh_tarefa_ativa=True
            ).order_by('-atualizado_em')  # Mais recente primeiro
            
            # Se tem mais de 1 ativa
            if ativas.count() > 1:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  {usuario.username} tem {ativas.count()} tarefas ativas (deve ter apenas 1)'
                    )
                )
                
                # Manter apenas a primeira (mais recente) ativa
                primeira_ativa = ativas.first()
                
                # Pausar todas as outras
                for tarefa in ativas[1:]:
                    tarefa.eh_tarefa_ativa = False
                    tarefa.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ NRORC {tarefa.pedido_mestre.nrorc} (ID={tarefa.id}) na etapa {tarefa.etapa_atual.nome} foi pausada'
                        )
                    )
                    total_corrigidos += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ NRORC {primeira_ativa.pedido_mestre.nrorc} (ID={primeira_ativa.id}) mantida ATIVA\n'
                    )
                )
        
        if total_corrigidos > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ {total_corrigidos} tarefa(s) foram pausadas com sucesso!')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✅ Nenhuma tarefa duplicada encontrada. Sistema está OK!')
            )
