from django.core.management.base import BaseCommand
from core.models import Exemplar, Reserva
from django.db.models import Q


class Command(BaseCommand):
    help = 'Verifica exemplares com situação possivelmente incorreta no banco'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== VERIFICAÇÃO DE EXEMPLARES ===\n'))

        # 1. Exemplares marcados como RESERVADO mas sem reserva ativa
        exemplares_reservado_sem_reserva = Exemplar.objects.filter(
            situacao=Exemplar.Situacao.RESERVADO
        ).exclude(
            reservas__status=Reserva.Status.CONFIRMADO
        ).distinct()

        if exemplares_reservado_sem_reserva.exists():
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  {exemplares_reservado_sem_reserva.count()} EXEMPLARES marcados como RESERVADO mas SEM reserva ativa:\n'
            ))
            for exemplar in exemplares_reservado_sem_reserva:
                self.stdout.write(f'   - {exemplar.codigo_exemplar} ({exemplar.item.nome})')
                # Mostrar reservas relacionadas
                reservas = exemplar.reservas.all()
                if reservas.exists():
                    for r in reservas:
                        self.stdout.write(f'     Reserva #{r.id}: {r.get_status_display()}')
                else:
                    self.stdout.write(f'     Nenhuma reserva vinculada')
        else:
            self.stdout.write(self.style.SUCCESS(
                '✅ Nenhum exemplar RESERVADO sem reserva ativa encontrado'
            ))

        # 2. Exemplares em EM_MANUTENCAO
        em_manutencao = Exemplar.objects.filter(
            situacao=Exemplar.Situacao.EM_MANUTENCAO
        )
        
        if em_manutencao.exists():
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  {em_manutencao.count()} EXEMPLARES em manutenção:\n'
            ))
            for exemplar in em_manutencao:
                self.stdout.write(f'   - {exemplar.codigo_exemplar} ({exemplar.item.nome}) - Condição: {exemplar.get_condicao_display()}')
        else:
            self.stdout.write(self.style.SUCCESS(
                '✅ Nenhum exemplar em manutenção'
            ))

        # 3. Resumo geral
        total = Exemplar.objects.count()
        disponiveis = Exemplar.objects.filter(situacao=Exemplar.Situacao.DISPONIVEL).count()
        reservados = Exemplar.objects.filter(situacao=Exemplar.Situacao.RESERVADO).count()
        manutencao = Exemplar.objects.filter(situacao=Exemplar.Situacao.EM_MANUTENCAO).count()

        self.stdout.write(self.style.SUCCESS(
            f'\n=== RESUMO ===\n'
            f'Total de exemplares: {total}\n'
            f'✅ Disponíveis: {disponiveis}\n'
            f'🔒 Reservados: {reservados}\n'
            f'🔧 Em manutenção: {manutencao}\n'
        ))

        # 4. Reservas ativas
        reservas_ativas = Reserva.objects.filter(
            status=Reserva.Status.CONFIRMADO
        )
        
        if reservas_ativas.exists():
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  {reservas_ativas.count()} RESERVAS ATIVAS encontradas:\n'
            ))
            for r in reservas_ativas:
                self.stdout.write(f'   Reserva #{r.id}: {r.usuario.nusp} - {r.item.codigo_tipo}')
                self.stdout.write(f'   Exemplar: {r.exemplar.codigo_exemplar if r.exemplar else "Nenhum"}')
        else:
            self.stdout.write(self.style.SUCCESS(
                '✅ Nenhuma reserva ativa encontrada'
            ))

        self.stdout.write(self.style.SUCCESS('\n=== FIM DA VERIFICAÇÃO ===\n'))
