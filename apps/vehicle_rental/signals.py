from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Rental, Vehicle, MaintenanceRecord


@receiver(pre_save, sender=Rental)
def update_rental_calculations(sender, instance, **kwargs):
    """Update rental calculations before saving"""
    if instance.start_date and instance.end_date:
        # Calculate number of days
        delta = instance.end_date - instance.start_date
        instance.number_of_days = max(1, delta.days)
        
        # Calculate amounts if daily_rate is set
        if instance.daily_rate:
            base_amount = instance.daily_rate * instance.number_of_days
            
            # Calculate commission amount based on either percentage or fixed amount
            commission = 0
            if instance.commission_percent is not None and instance.commission_percent > 0:
                # Use percentage-based commission
                commission = (base_amount * instance.commission_percent) / 100
                instance.commission_amount = None  # Clear the fixed amount
            elif instance.commission_amount is not None and instance.commission_amount > 0:
                # Use fixed amount commission
                commission = instance.commission_amount
                instance.commission_percent = None  # Clear the percentage
            else:
                # No commission - clear both fields
                instance.commission_percent = None
                instance.commission_amount = None
                
            # Subtotal is base amount minus commission
            instance.subtotal = base_amount - commission
            
            # Total amount includes additional fees
            instance.total_amount = (
                instance.subtotal + 
                (instance.insurance_fee or 0) + 
                (instance.late_return_fee or 0) + 
                (instance.damage_fee or 0)
            )


@receiver(post_save, sender=Rental)
def update_vehicle_status_on_rental(sender, instance, created, **kwargs):
    """Update vehicle status when rental is created or updated"""
    vehicle = instance.vehicle
    now = timezone.now()
    
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
    
    if current_active_rental or confirmed_current_rental:
        # Vehicle should be rented because there's an active rental right now
        if vehicle.status != 'rented':
            vehicle.status = 'rented'
            vehicle.save(update_fields=['status'])
    else:
        # No current active rental
        # Check if vehicle is in maintenance
        from .models import MaintenanceRecord
        active_maintenance = MaintenanceRecord.objects.filter(
            vehicle=vehicle,
            status='in_progress'
        ).exists()
        
        if not active_maintenance and vehicle.status != 'available':
            vehicle.status = 'available'
            vehicle.save(update_fields=['status'])
    
    # Update vehicle mileage if rental is completed and mileage_end is provided
    if instance.status == 'completed' and instance.mileage_end and instance.mileage_end > vehicle.mileage:
        vehicle.mileage = instance.mileage_end
        vehicle.save(update_fields=['mileage'])


@receiver(post_save, sender=MaintenanceRecord)
def update_vehicle_status_on_maintenance(sender, instance, created, **kwargs):
    """Update vehicle status when maintenance is scheduled or completed"""
    if instance.status == 'in_progress':
        instance.vehicle.status = 'maintenance'
        instance.vehicle.save(update_fields=['status'])
    
    elif instance.status == 'completed':
        # Check if there are any other maintenance records in progress
        other_maintenance = MaintenanceRecord.objects.filter(
            vehicle=instance.vehicle,
            status='in_progress'
        ).exclude(pk=instance.pk)
        
        if not other_maintenance.exists():
            # Check if vehicle has any active rentals
            active_rentals = Rental.objects.filter(
                vehicle=instance.vehicle,
                status='active'
            ).exists()
            
            if active_rentals:
                instance.vehicle.status = 'rented'
            else:
                instance.vehicle.status = 'available'
            
            instance.vehicle.save(update_fields=['status'])


@receiver(pre_save, sender=MaintenanceRecord)
def update_maintenance_calculations(sender, instance, **kwargs):
    """Update maintenance cost calculations before saving"""
    instance.total_cost = instance.labor_cost + instance.parts_cost + instance.other_costs
