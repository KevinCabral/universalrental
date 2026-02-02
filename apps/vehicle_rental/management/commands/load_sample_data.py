from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.vehicle_rental.models import VehicleBrand, Vehicle, Customer, ExpenseCategory
from decimal import Decimal
import random
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Load sample data for vehicle rental system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading sample data...'))

        # Create Vehicle Brands
        brands_data = [
            ('Toyota', 'Japan'),
            ('Ford', 'USA'),
            ('Nissan', 'Japan'),
            ('Hyundai', 'South Korea'),
            ('Mazda', 'Japan'),
            ('Volkswagen', 'Germany'),
            ('Honda', 'Japan'),
            ('Chevrolet', 'USA'),
        ]

        for brand_name, country in brands_data:
            brand, created = VehicleBrand.objects.get_or_create(
                name=brand_name,
                defaults={'country_of_origin': country}
            )
            if created:
                self.stdout.write(f'Created brand: {brand_name}')

        # Create Expense Categories
        categories_data = [
            ('Fuel', 'Fuel costs and refueling expenses'),
            ('Maintenance', 'Regular maintenance and servicing costs'),
            ('Repairs', 'Repair costs for damages and breakdowns'),
            ('Insurance', 'Insurance premiums and claims'),
            ('Registration', 'Vehicle registration and licensing fees'),
            ('Cleaning', 'Vehicle cleaning and detailing costs'),
            ('Parking', 'Parking fees and tolls'),
            ('Other', 'Miscellaneous expenses'),
        ]

        for cat_name, description in categories_data:
            category, created = ExpenseCategory.objects.get_or_create(
                name=cat_name,
                defaults={'description': description}
            )
            if created:
                self.stdout.write(f'Created expense category: {cat_name}')

        # Create Sample Vehicles
        toyota = VehicleBrand.objects.get(name='Toyota')
        ford = VehicleBrand.objects.get(name='Ford')
        nissan = VehicleBrand.objects.get(name='Nissan')

        vehicles_data = [
            {
                'brand': toyota,
                'model': 'Corolla',
                'year': 2020,
                'chassis_number': 'JTDEPRAE8LJ012345',
                'registration_number': 'ABC-123',
                'color': 'White',
                'engine_size': 1800,
                'fuel_type': 'petrol',
                'gearbox_type': 'automatic',
                'daily_rate': Decimal('150.00'),
                'purchase_price': Decimal('15000.00'),
                'mileage': 25000,
            },
            {
                'brand': ford,
                'model': 'Ranger',
                'year': 2019,
                'chassis_number': 'MAJ6P1TL8KC123456',
                'registration_number': 'DEF-456',
                'color': 'Blue',
                'engine_size': 2200,
                'fuel_type': 'diesel',
                'gearbox_type': 'manual',
                'daily_rate': Decimal('200.00'),
                'purchase_price': Decimal('25000.00'),
                'mileage': 35000,
            },
            {
                'brand': nissan,
                'model': 'Sentra',
                'year': 2021,
                'chassis_number': '3N1AB7AP5MY789012',
                'registration_number': 'GHI-789',
                'color': 'Red',
                'engine_size': 1600,
                'fuel_type': 'petrol',
                'gearbox_type': 'cvt',
                'daily_rate': Decimal('120.00'),
                'purchase_price': Decimal('18000.00'),
                'mileage': 15000,
            },
        ]

        for vehicle_data in vehicles_data:
            vehicle_data['date_of_purchase'] = date.today() - timedelta(days=random.randint(100, 1000))
            vehicle, created = Vehicle.objects.get_or_create(
                registration_number=vehicle_data['registration_number'],
                defaults=vehicle_data
            )
            if created:
                self.stdout.write(f'Created vehicle: {vehicle_data["registration_number"]}')

        # Create Sample Customers
        customers_data = [
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@email.com',
                'phone_number': '+260 97 123 4567',
                'address_line_1': '123 Main Street',
                'city': 'Lusaka',
                'postal_code': '10101',
                'country': 'Zambia',
                'id_number': 'ID123456789',
                'driving_license_number': 'DL123456789',
                'license_expiry_date': date.today() + timedelta(days=365),
            },
            {
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane.smith@email.com',
                'phone_number': '+260 97 234 5678',
                'address_line_1': '456 Oak Avenue',
                'city': 'Kitwe',
                'postal_code': '20202',
                'country': 'Zambia',
                'id_number': 'ID234567890',
                'driving_license_number': 'DL234567890',
                'license_expiry_date': date.today() + timedelta(days=500),
            },
            {
                'first_name': 'Michael',
                'last_name': 'Johnson',
                'email': 'michael.johnson@email.com',
                'phone_number': '+260 97 345 6789',
                'address_line_1': '789 Pine Road',
                'city': 'Ndola',
                'postal_code': '30303',
                'country': 'Zambia',
                'id_number': 'ID345678901',
                'driving_license_number': 'DL345678901',
                'license_expiry_date': date.today() + timedelta(days=800),
            },
        ]

        for customer_data in customers_data:
            customer, created = Customer.objects.get_or_create(
                email=customer_data['email'],
                defaults=customer_data
            )
            if created:
                self.stdout.write(f'Created customer: {customer_data["email"]}')

        self.stdout.write(
            self.style.SUCCESS('Successfully loaded sample data!')
        )
