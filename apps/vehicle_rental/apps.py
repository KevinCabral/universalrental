from django.apps import AppConfig


class VehicleRentalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.vehicle_rental'
    verbose_name = 'Vehicle Rental Management'
    
    def ready(self):
        import apps.vehicle_rental.signals
