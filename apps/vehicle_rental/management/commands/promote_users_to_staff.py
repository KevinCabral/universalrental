"""
Comando para promover usuários regulares a staff.
Permite que usuários específicos tenham acesso ao sistema.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Promove usuários não-staff para staff, permitindo login no sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Promover usuário específico por username',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Promover todos os usuários ativos não-staff para staff',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar o que seria feito sem fazer alterações',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        username = options.get('username')
        promote_all = options.get('all', False)
        
        if not username and not promote_all:
            self.stdout.write(
                self.style.ERROR('Erro: Especifique --username ou --all')
            )
            return
        
        if username:
            # Promover usuário específico
            try:
                user = User.objects.get(username=username)
                if user.is_staff:
                    self.stdout.write(
                        self.style.WARNING(f'✓ {username} já é staff')
                    )
                else:
                    if dry_run:
                        self.stdout.write(f'[DRY RUN] Promoveria {username} para staff')
                    else:
                        user.is_staff = True
                        user.is_active = True
                        user.save()
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ {username} promovido para staff com sucesso')
                        )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Erro: Usuário "{username}" não encontrado')
                )
        
        elif promote_all:
            # Promover todos os usuários não-staff ativos
            non_staff_users = User.objects.filter(
                is_staff=False,
                is_active=True
            )
            
            count = non_staff_users.count()
            
            if count == 0:
                self.stdout.write(
                    self.style.SUCCESS('✓ Nenhum usuário não-staff ativo encontrado')
                )
                return
            
            self.stdout.write(f'\n=== Promover {count} usuário(s) para staff ===\n')
            
            if dry_run:
                self.stdout.write(self.style.WARNING('=== DRY RUN - Nenhuma alteração será feita ===\n'))
            
            for user in non_staff_users:
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] Promoveria: {user.username} ({user.email})')
                else:
                    user.is_staff = True
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ {user.username} ({user.email})')
                    )
            
            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'\n✓ {count} usuário(s) promovido(s) para staff com sucesso!')
                )
                self.stdout.write(
                    self.style.SUCCESS('Estes usuários agora podem fazer login no sistema.')
                )
