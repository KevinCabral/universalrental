from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from apps.vehicle_rental.models import (
    VehicleBrand, Vehicle, Customer, Rental, Expense, 
    MaintenanceRecord, ExpenseCategory
)
from decimal import Decimal
import random
from datetime import date, timedelta, datetime


class Command(BaseCommand):
    help = 'Load comprehensive sample data for reports dashboard testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--months',
            type=int,
            default=12,
            help='Number of months of historical data to generate'
        )

    def handle(self, *args, **options):
        months = options['months']
        self.stdout.write(self.style.SUCCESS(f'Loading {months} months of sample data...'))

        # Ensure we have basic data first
        self.create_basic_data()
        
        # Create historical data
        self.create_historical_rentals(months)
        self.create_historical_expenses(months)
        self.create_historical_maintenance(months)

        self.stdout.write(
            self.style.SUCCESS('Successfully loaded comprehensive sample data!')
        )

    def create_basic_data(self):
        """Ensure we have basic master data"""
        
        # Create admin user if not exists
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@rentalsystem.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write('Created admin user')

        # Create Vehicle Brands
        brands_data = [
            ('Toyota', 'Japan'), ('Ford', 'USA'), ('Nissan', 'Japan'),
            ('Hyundai', 'South Korea'), ('Mazda', 'Japan'), ('Volkswagen', 'Germany'),
            ('Honda', 'Japan'), ('Chevrolet', 'USA'), ('BMW', 'Germany'), ('Mercedes', 'Germany')
        ]

        for brand_name, country in brands_data:
            VehicleBrand.objects.get_or_create(
                name=brand_name,
                defaults={'country_of_origin': country}
            )

        # Create Expense Categories
        categories_data = [
            ('Combustível', 'Custos de combustível e abastecimento'),
            ('Manutenção', 'Custos regulares de manutenção e serviços'),
            ('Reparações', 'Custos de reparação por danos e avarias'),
            ('Seguro', 'Prémios de seguro e reclamações'),
            ('Licenciamento', 'Taxas de registo e licenciamento de veículos'),
            ('Limpeza', 'Custos de limpeza e detalhamento de veículos'),
            ('Estacionamento', 'Taxas de estacionamento e portagens'),
            ('Multas', 'Multas de trânsito e infrações'),
            ('Outros', 'Despesas diversas'),
        ]

        for cat_name, description in categories_data:
            ExpenseCategory.objects.get_or_create(
                name=cat_name,
                defaults={'description': description}
            )

        # Create Sample Vehicles (expand the fleet)
        brands = list(VehicleBrand.objects.all())
        vehicle_models = [
            ('Toyota', 'Corolla', 1800, 'petrol', 'automatic', 150),
            ('Toyota', 'RAV4', 2000, 'petrol', 'automatic', 200),
            ('Ford', 'Ranger', 2200, 'diesel', 'manual', 220),
            ('Ford', 'Fiesta', 1400, 'petrol', 'manual', 120),
            ('Nissan', 'Sentra', 1600, 'petrol', 'cvt', 140),
            ('Nissan', 'X-Trail', 2500, 'petrol', 'automatic', 190),
            ('Hyundai', 'Elantra', 1600, 'petrol', 'automatic', 135),
            ('Hyundai', 'Tucson', 2000, 'petrol', 'automatic', 185),
            ('Mazda', 'CX-5', 2200, 'petrol', 'automatic', 175),
            ('Volkswagen', 'Polo', 1400, 'petrol', 'manual', 125),
            ('Honda', 'Civic', 1800, 'petrol', 'cvt', 155),
            ('BMW', 'X3', 2800, 'petrol', 'automatic', 350),
            ('Mercedes', 'C-Class', 2000, 'petrol', 'automatic', 400),
        ]

        for i, (brand_name, model, engine, fuel, gearbox, daily_rate) in enumerate(vehicle_models, 1):
            brand = VehicleBrand.objects.get(name=brand_name)
            reg_number = f'{brand_name[:3].upper()}-{i:03d}'
            
            Vehicle.objects.get_or_create(
                registration_number=reg_number,
                defaults={
                    'brand': brand,
                    'model': model,
                    'year': random.randint(2018, 2023),
                    'chassis_number': f'CHASSIS{i:010d}',
                    'color': random.choice(['White', 'Black', 'Silver', 'Blue', 'Red', 'Gray']),
                    'engine_size': engine,
                    'fuel_type': fuel,
                    'gearbox_type': gearbox,
                    'daily_rate': Decimal(str(daily_rate)),
                    'purchase_price': Decimal(str(daily_rate * 100)),
                    'mileage': random.randint(10000, 80000),
                    'date_of_purchase': date.today() - timedelta(days=random.randint(100, 1500)),
                    'status': 'available',
                }
            )

        # Create Sample Customers
        customers_data = [
            ('João', 'Silva', 'joao.silva@email.com', '+260 97 123 4567', 'Lusaka'),
            ('Maria', 'Santos', 'maria.santos@email.com', '+260 97 234 5678', 'Kitwe'),
            ('António', 'Ferreira', 'antonio.ferreira@email.com', '+260 97 345 6789', 'Ndola'),
            ('Ana', 'Costa', 'ana.costa@email.com', '+260 97 456 7890', 'Lusaka'),
            ('Paulo', 'Oliveira', 'paulo.oliveira@email.com', '+260 97 567 8901', 'Livingstone'),
            ('Sofia', 'Rodrigues', 'sofia.rodrigues@email.com', '+260 97 678 9012', 'Kitwe'),
            ('Carlos', 'Pereira', 'carlos.pereira@email.com', '+260 97 789 0123', 'Lusaka'),
            ('Isabel', 'Almeida', 'isabel.almeida@email.com', '+260 97 890 1234', 'Ndola'),
            ('Ricardo', 'Gomes', 'ricardo.gomes@email.com', '+260 97 901 2345', 'Lusaka'),
            ('Cristina', 'Martins', 'cristina.martins@email.com', '+260 97 012 3456', 'Kitwe'),
        ]

        for i, (first_name, last_name, email, phone, city) in enumerate(customers_data, 1):
            Customer.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone,
                    'address_line_1': f'{random.randint(100, 999)} Rua Principal',
                    'city': city,
                    'postal_code': f'{random.randint(10000, 99999)}',
                    'country': 'Zambia',
                    'id_number': f'ID{i:09d}',
                    'driving_license_number': f'DL{i:09d}',
                    'license_expiry_date': date.today() + timedelta(days=random.randint(30, 1095)),
                }
            )

    def create_historical_rentals(self, months):
        """Create historical rental data"""
        customers = list(Customer.objects.all())
        vehicles = list(Vehicle.objects.all())
        
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)
        
        # Generate 3-8 rentals per month
        total_rentals = months * random.randint(3, 8) * len(vehicles) // 3
        
        for _ in range(total_rentals):
            # Random rental date in the period
            rental_date = start_date + timedelta(
                days=random.randint(0, (end_date - start_date).days)
            )
            
            # Random rental duration (1-14 days)
            duration = random.randint(1, 14)
            start_rental = timezone.make_aware(timezone.datetime.combine(rental_date, timezone.datetime.min.time()))
            end_rental = start_rental + timedelta(days=duration)
            
            customer = random.choice(customers)
            vehicle = random.choice(vehicles)
            
            daily_rate = vehicle.daily_rate
            subtotal = daily_rate * duration
            
            # Random commission (5-15%)
            commission_percent = Decimal(str(random.randint(5, 15)))
            commission_amount = subtotal * commission_percent / 100
            
            # Random additional fees
            late_fee = Decimal('0.00')
            damage_fee = Decimal('0.00')
            security_deposit = subtotal * Decimal('0.2')  # 20% deposit
            
            if random.random() < 0.1:  # 10% chance of late return
                late_fee = daily_rate * Decimal('0.5')
            
            if random.random() < 0.05:  # 5% chance of damage
                damage_fee = Decimal(str(random.randint(50, 500)))
            
            total_amount = subtotal + commission_amount + late_fee + damage_fee
            
            # Determine status based on dates
            today = timezone.now()
            if end_rental < today:
                status = 'completed'
                actual_return_date = end_rental + timedelta(days=random.randint(0, 2))
            elif start_rental <= today <= end_rental:
                status = 'active'
                actual_return_date = None
            elif start_rental > today:
                status = 'confirmed'
                actual_return_date = None
            else:
                status = random.choice(['confirmed', 'pending'])
                actual_return_date = None
            
            # Fuel level choices
            fuel_choices = ['empty', 'quarter', 'half', 'three_quarter', 'full']
            
            Rental.objects.create(
                customer=customer,
                vehicle=vehicle,
                start_date=start_rental,
                end_date=end_rental,
                actual_return_date=actual_return_date,
                daily_rate=daily_rate,
                number_of_days=duration,
                subtotal=subtotal,
                commission_percent=commission_percent,
                commission_amount=commission_amount,
                late_return_fee=late_fee,
                damage_fee=damage_fee,
                security_deposit=security_deposit,
                total_amount=total_amount,
                status=status,
                mileage_start=random.randint(50000, 100000),
                mileage_end=random.randint(50000, 100000) + (duration * random.randint(50, 200)) if status == 'completed' else None,
                fuel_level_start=random.choice(fuel_choices),
                fuel_level_end=random.choice(fuel_choices) if status == 'completed' else None,
                notes=f'Aluguer de {duration} dias' if random.random() < 0.3 else '',
            )

        self.stdout.write(f'Created {total_rentals} rental records')

    def create_historical_expenses(self, months):
        """Create historical expense data"""
        categories = list(ExpenseCategory.objects.all())
        vehicles = list(Vehicle.objects.all())
        rentals = list(Rental.objects.all())
        admin_user = User.objects.filter(is_staff=True).first()
        
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)
        
        # Generate 2-5 expenses per vehicle per month
        total_expenses = months * len(vehicles) * random.randint(2, 5)
        
        for _ in range(total_expenses):
            expense_date = start_date + timedelta(
                days=random.randint(0, (end_date - start_date).days)
            )
            
            category = random.choice(categories)
            
            # Amount based on category
            if category.name == 'Combustível':
                amount = Decimal(str(random.randint(20, 80)))
            elif category.name in ['Manutenção', 'Reparações']:
                amount = Decimal(str(random.randint(100, 1000)))
            elif category.name == 'Seguro':
                amount = Decimal(str(random.randint(200, 800)))
            elif category.name == 'Multas':
                amount = Decimal(str(random.randint(50, 300)))
            else:
                amount = Decimal(str(random.randint(20, 200)))
            
            description = f'{category.name} - {expense_date.strftime("%B %Y")}'
            
            # Some expenses are related to rentals
            related_rental = random.choice(rentals) if random.random() < 0.3 else None
            related_vehicle = related_rental.vehicle if related_rental else random.choice(vehicles)
            
            Expense.objects.create(
                category=category,
                description=description,
                amount=amount,
                date=expense_date,
                rental=related_rental,
                vehicle=related_vehicle,
                receipt_number=f'REC{random.randint(100000, 999999)}',
                vendor=random.choice([
                    'Estação de Serviço Shell', 'Total Energies', 'BP Zambia',
                    'AutoParts Lusaka', 'Manutenção Express', 'ServiçoRápido'
                ]),
                is_approved=random.choice([True, False]),
                created_by=admin_user,
            )

        self.stdout.write(f'Created {total_expenses} expense records')

    def create_historical_maintenance(self, months):
        """Create historical maintenance data"""
        vehicles = list(Vehicle.objects.all())
        admin_user = User.objects.filter(is_staff=True).first()
        
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)
        
        # Generate 1-3 maintenance records per vehicle per month
        total_maintenance = months * len(vehicles) * random.randint(1, 3)
        
        maintenance_types = ['scheduled', 'repair', 'inspection', 'warranty', 'accident']
        service_providers = [
            'AutoServiço Lusaka', 'Oficina Central', 'Garage Premium',
            'ServiçoExpress', 'Manutenção Profissional', 'AutoCare Zambia'
        ]
        
        for _ in range(total_maintenance):
            scheduled_date = start_date + timedelta(
                days=random.randint(0, (end_date - start_date).days)
            )
            
            vehicle = random.choice(vehicles)
            maintenance_type = random.choice(maintenance_types)
            
            # Determine status and completion
            today = date.today()
            if scheduled_date < today - timedelta(days=7):
                status = 'completed'
                completed_date = scheduled_date + timedelta(days=random.randint(0, 3))
            elif scheduled_date < today:
                status = random.choice(['completed', 'in_progress'])
                completed_date = scheduled_date + timedelta(days=random.randint(0, 2)) if status == 'completed' else None
            else:
                status = 'scheduled'
                completed_date = None
            
            # Costs based on type
            if maintenance_type == 'scheduled':
                labor_cost = Decimal(str(random.randint(100, 300)))
                parts_cost = Decimal(str(random.randint(50, 200)))
            elif maintenance_type == 'repair':
                labor_cost = Decimal(str(random.randint(200, 800)))
                parts_cost = Decimal(str(random.randint(100, 1000)))
            elif maintenance_type == 'inspection':
                labor_cost = Decimal(str(random.randint(50, 150)))
                parts_cost = Decimal(str(random.randint(0, 50)))
            else:
                labor_cost = Decimal(str(random.randint(150, 500)))
                parts_cost = Decimal(str(random.randint(50, 400)))
            
            other_costs = Decimal(str(random.randint(0, 100)))
            total_cost = labor_cost + parts_cost + other_costs
            
            MaintenanceRecord.objects.create(
                vehicle=vehicle,
                maintenance_type=maintenance_type,
                date_scheduled=scheduled_date,
                date_completed=completed_date,
                mileage=vehicle.mileage + random.randint(0, 10000),
                service_description=f'Manutenção {maintenance_type} - {vehicle.model}',
                parts_replaced=f'Peças para {maintenance_type}' if parts_cost > 0 else '',
                service_provider=random.choice(service_providers),
                labor_cost=labor_cost if status == 'completed' else Decimal('0.00'),
                parts_cost=parts_cost if status == 'completed' else Decimal('0.00'),
                other_costs=other_costs if status == 'completed' else Decimal('0.00'),
                total_cost=total_cost if status == 'completed' else Decimal('0.00'),
                invoice_number=f'INV{random.randint(100000, 999999)}' if status == 'completed' else '',
                warranty_until=completed_date + timedelta(days=random.randint(30, 365)) if completed_date else None,
                status=status,
                next_service_mileage=vehicle.mileage + random.randint(5000, 15000) if status == 'completed' else None,
                next_service_date=completed_date + timedelta(days=random.randint(90, 365)) if completed_date else None,
                created_by=admin_user,
            )

        self.stdout.write(f'Created {total_maintenance} maintenance records')
