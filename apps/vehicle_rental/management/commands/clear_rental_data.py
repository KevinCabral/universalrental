from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from apps.vehicle_rental.models import (
    RentalPhoto, RentalEvaluation, CustomerNotification,
    Rental, Customer, MaintenanceRecord, Expense,
    VehiclePhoto, DeliveryLocation
)


class Command(BaseCommand):
    help = "Limpa todos os dados de aluguer e usuÃ¡rios nÃ£o-superuser"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Executa sem pedir confirmaÃ§Ã£o'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o que serÃ¡ apagado sem executar'
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("LIMPEZA DE DADOS DE ALUGUER")
        self.stdout.write("=" * 60)

        # í ½íº¨ SeguranÃ§a: bloquear em produÃ§Ã£o
        if not settings.DEBUG and not options['force']:
            self.stdout.write(self.style.ERROR(
                "â BLOQUEADO: NÃ£o execute em produÃ§Ã£o sem --force"
            ))
            return

        # í ½í³ Contagem inicial
        counts = {
            "RentalPhoto": RentalPhoto.objects.count(),
            "RentalEvaluation": RentalEvaluation.objects.count(),
            "CustomerNotification": CustomerNotification.objects.count(),
            "Rental": Rental.objects.count(),
            "Customer": Customer.objects.count(),
            "MaintenanceRecord": MaintenanceRecord.objects.count(),
            "Expense": Expense.objects.count(),
            "VehiclePhoto": VehiclePhoto.objects.count(),
            "DeliveryLocation": DeliveryLocation.objects.count(),
            "User (non-superuser)": User.objects.filter(is_superuser=False).count(),
        }

        self.stdout.write("\ní ½í³ Dados encontrados:")
        for model, count in counts.items():
            self.stdout.write(f"   - {model}: {count}")

        # í ½í´ Dry run (preview)
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\nâ ï¸ DRY RUN - Nada foi apagado"))
            return

        # â ConfirmaÃ§Ã£o
        if not options['force']:
            confirm = input("\nDigite 'SIM' para confirmar exclusÃ£o: ")
            if confirm != "SIM":
                self.stdout.write(self.style.WARNING("â OperaÃ§Ã£o cancelada."))
                return

        self.stdout.write("\ní ½íº Iniciando exclusÃ£o...\n")

        try:
            deleted_counts = {}

            # Ordem correta por dependÃªncias
            deleted_counts['RentalPhoto'] = RentalPhoto.objects.all().delete()[0]
            deleted_counts['RentalEvaluation'] = RentalEvaluation.objects.all().delete()[0]
            deleted_counts['CustomerNotification'] = CustomerNotification.objects.all().delete()[0]
            deleted_counts['Rental'] = Rental.objects.all().delete()[0]
            deleted_counts['Customer'] = Customer.objects.all().delete()[0]
            deleted_counts['MaintenanceRecord'] = MaintenanceRecord.objects.all().delete()[0]
            deleted_counts['Expense'] = Expense.objects.all().delete()[0]
            deleted_counts['VehiclePhoto'] = VehiclePhoto.objects.all().delete()[0]
            deleted_counts['DeliveryLocation'] = DeliveryLocation.objects.all().delete()[0]
            deleted_counts['User'] = User.objects.filter(is_superuser=False).delete()[0]

            # â Resultado
            self.stdout.write(self.style.SUCCESS("\nâ EXCLUSÃO CONCLUÃDA!\n"))
            self.stdout.write("í ½í³ Resumo:")

            for model, count in deleted_counts.items():
                if count > 0:
                    self.stdout.write(f"   - {model}: {count} registros")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nâ ERRO: {str(e)}"))
            raise