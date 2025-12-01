from django.core.management.base import BaseCommand
from core.models import Exemplar, Reserva


class Command(BaseCommand):
    help = 'Corrige exemplares com situação incorreta (RESERVADO sem reserva ativa)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== CORRIGINDO EXEMPLARES ===\n'))

        # Encontrar exemplares marcados como RESERVADO mas sem reserva ativa
        exemplares_incorretos = Exemplar.objects.filter(
            situacao=Exemplar.Situacao.RESERVADO
        ).exclude(
            reservas__status=Reserva.Status.CONFIRMADO
        ).distinct()

        if exemplares_incorretos.exists():
            self.stdout.write(self.style.WARNING(
                f'Encontrados {exemplares_incorretos.count()} exemplares para corrigir:\n'
            ))
            
            for exemplar in exemplares_incorretos:
                old_situacao = exemplar.get_situacao_display()
                exemplar.situacao = Exemplar.Situacao.DISPONIVEL
                exemplar.save()
                
                self.stdout.write(
                    f'✅ {exemplar.codigo_exemplar} ({exemplar.item.nome}): '
                    f'{old_situacao} → {exemplar.get_situacao_display()}'
                )
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ {exemplares_incorretos.count()} exemplares corrigidos com sucesso!\n'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                '✅ Nenhum exemplar incorreto encontrado\n'
            ))
