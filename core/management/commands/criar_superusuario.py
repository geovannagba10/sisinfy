from django.core.management.base import BaseCommand
from core.models import Usuario
import os


class Command(BaseCommand):
    help = 'Cria um superusuário automaticamente'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
        
        if not Usuario.objects.filter(username=username).exists():
            Usuario.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                nome_completo='Administrador',
                nusp='000000000'
            )
            self.stdout.write(self.style.SUCCESS(f'Superusuário "{username}" criado com sucesso!'))
        else:
            self.stdout.write(self.style.WARNING(f'Superusuário "{username}" já existe.'))
