from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.vehicle_rental.models import Vehicle, Rental, MaintenanceRecord


class Command(BaseCommand):
    help = 'Update all vehicle statuses based on current rentals and maintenance'

    def handle(self, *args, **options):
        self.stdout.write("Updating vehicle statuses...")
        
        updated_count = 0
        now = timezone.now()
        
        for vehicle in Vehicle.objects.filter(is_active=True):
            old_status = vehicle.status
            
            # Check for currently active rentals (rental period that includes current time)
            current_active_rental = vehicle.rentals.filter(
                status='active',
                start_date__lte=now,
                end_date__gte=now
            ).first()
            
            # Check for confirmed future rentals that should be active now
            confirmed_current_rental = vehicle.rentals.filter(
                status='confirmed',
                start_date__lte=now,
                end_date__gte=now
            ).first()
            
            # Check if vehicle is in maintenance
            active_maintenance = MaintenanceRecord.objects.filter(
                vehicle=vehicle,
                status='in_progress'
            ).exists()
            
            # Determine correct status
            if active_maintenance:
                new_status = 'maintenance'
            elif current_active_rental or confirmed_current_rental:
                new_status = 'rented'
            else:
                new_status = 'available'
            
            # Update if status changed
            if vehicle.status != new_status:
                vehicle.status = new_status
                vehicle.save(update_fields=['status'])
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated {vehicle} from "{old_status}" to "{new_status}"'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} vehicle statuses'
            )
        )