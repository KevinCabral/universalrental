from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import (
    Vehicle, VehicleBrand, Customer, Rental, Expense, ExpenseCategory,
    MaintenanceRecord, RentalPhoto, DeliveryLocation, SystemConfiguration
)


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            'brand', 'model', 'year', 'description', 'chassis_number', 'registration_number',
            'color', 'photo', 'engine_size', 'fuel_type', 'gearbox_type', 'panoramic_roof',
            'air_conditioning', 'number_of_seats', 'mileage', 'purchase_price',
            'date_of_purchase', 'daily_rate', 'status'
        ]
        labels = {
            'brand': 'Marca',
            'model': 'Modelo',
            'year': 'Ano',
            'description': 'Descrição',
            'chassis_number': 'Número do Chassis',
            'registration_number': 'Matrícula',
            'color': 'Cor',
            'photo': 'Foto do Veículo',
            'engine_size': 'Cilindrada (cc)',
            'fuel_type': 'Tipo de Combustível',
            'gearbox_type': 'Tipo de Transmissão',
            'panoramic_roof': 'Teto Panorâmico',
            'air_conditioning': 'Ar Condicionado',
            'number_of_seats': 'Número de Lugares',
            'mileage': 'Quilometragem',
            'purchase_price': 'Preço de Compra',
            'date_of_purchase': 'Data de Compra',
            'daily_rate': 'Tarifa Diária',
            'status': 'Estado'
        }
        widgets = {
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1900'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Adicione informações adicionais sobre o veículo...'}),
            'date_of_purchase': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'chassis_number': forms.TextInput(attrs={'placeholder': 'Vehicle Identification Number', 'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'placeholder': 'License plate number', 'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'engine_size': forms.NumberInput(attrs={'min': '0', 'step': '0.1', 'class': 'form-control'}),
            'fuel_type': forms.Select(attrs={'class': 'form-control'}),
            'gearbox_type': forms.Select(attrs={'class': 'form-control'}),
            'panoramic_roof': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'air_conditioning': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'number_of_seats': forms.NumberInput(attrs={'min': '1', 'max': '50', 'class': 'form-control'}),
            'mileage': forms.NumberInput(attrs={'min': '0', 'class': 'form-control'}),
            'purchase_price': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'class': 'form-control'}),
            'daily_rate': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make certain fields optional
        self.fields['purchase_price'].required = False
        self.fields['date_of_purchase'].required = False
        self.fields['chassis_number'].required = False
    
    def clean_year(self):
        year = self.cleaned_data['year']
        current_year = timezone.now().year
        if year < 1900 or year > current_year + 1:
            raise ValidationError(f'O ano deve estar entre 1900 e {current_year + 1}')
        return year
    
    def clean_chassis_number(self):
        chassis_number = self.cleaned_data['chassis_number']
        if chassis_number and Vehicle.objects.filter(chassis_number=chassis_number).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError('Já existe um veículo com este número de chassis.')
        return chassis_number
    
    def clean_registration_number(self):
        registration_number = self.cleaned_data['registration_number']
        if Vehicle.objects.filter(registration_number=registration_number).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError('Já existe um veículo com esta matrícula.')
        return registration_number


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'birth_date',
            'address_line_1', 'address_line_2', 'city', 'postal_code', 'country',
            'id_number', 'driving_license_number', 'license_issue_date', 'license_expiry_date'
        ]
        labels = {
            'first_name': 'Primeiro Nome',
            'last_name': 'Apelido',
            'email': 'Email',
            'phone_number': 'Número de Telefone',
            'birth_date': 'Data de Nascimento',
            'address_line_1': 'Morada (Linha 1)',
            'address_line_2': 'Morada (Linha 2)',
            'city': 'Cidade',
            'postal_code': 'Código Postal',
            'country': 'País',
            'id_number': 'Número de Identificação',
            'driving_license_number': 'Número da Carta de Condução',
            'license_issue_date': 'Data de Emissão da Carta',
            'license_expiry_date': 'Data de Validade da Carta'
        }
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'license_issue_date': forms.DateInput(attrs={'type': 'date'}),
            'license_expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'email': forms.EmailInput(),
            'phone_number': forms.TextInput(attrs={'placeholder': '+260'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make certain fields optional
        self.fields['address_line_1'].required = False
        self.fields['email'].required = False
        self.fields['postal_code'].required = False
        self.fields['id_number'].required = False
        self.fields['license_expiry_date'].required = False
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if email:
            existing_customer = Customer.objects.filter(email=email).exclude(pk=self.instance.pk if self.instance else None).first()
            if existing_customer:
                # Only raise error if customer already has a user account
                if existing_customer.user is not None:
                    raise ValidationError('Já existe um cliente com este email.')
        return email
    
    def clean_id_number(self):
        id_number = self.cleaned_data['id_number']
        if id_number and Customer.objects.filter(id_number=id_number).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError('Já existe um cliente com este número de identificação.')
        return id_number
    
    def clean_driving_license_number(self):
        license_number = self.cleaned_data['driving_license_number']
        if license_number:
            existing_customer = Customer.objects.filter(driving_license_number=license_number).exclude(pk=self.instance.pk if self.instance else None).first()
            if existing_customer:
                # Only raise error if customer already has a user account
                if existing_customer.user is not None:
                    raise ValidationError('Já existe um cliente com este número de carta de condução.')
        return license_number
    
    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            if birth_date >= timezone.now().date():
                raise ValidationError('A data de nascimento deve ser no passado.')
            
            # Check minimum age (18 years)
            from dateutil.relativedelta import relativedelta
            min_age_date = timezone.now().date() - relativedelta(years=18)
            if birth_date > min_age_date:
                raise ValidationError('O cliente deve ter pelo menos 18 anos.')
        
        return birth_date
    
    def clean_license_issue_date(self):
        issue_date = self.cleaned_data.get('license_issue_date')
        if issue_date and issue_date > timezone.now().date():
            raise ValidationError('A data de emissão da carta não pode ser no futuro.')
        return issue_date
    
    def clean_license_expiry_date(self):
        expiry_date = self.cleaned_data.get('license_expiry_date')
        issue_date = self.cleaned_data.get('license_issue_date')
        
        if expiry_date and expiry_date <= timezone.now().date():
            raise ValidationError('A data de validade da carta deve ser no futuro.')
        
        if issue_date and expiry_date and expiry_date <= issue_date:
            raise ValidationError('A data de validade deve ser posterior à data de emissão.')
            
        return expiry_date


class RentalForm(forms.ModelForm):
    # Campo calculado para mostrar o total estimado
    total_estimate = forms.DecimalField(
        required=False,
        label='Total Estimado (ECV)',
        widget=forms.NumberInput(attrs={'readonly': True, 'class': 'form-control', 'style': 'background-color: #f8f9fa;'}),
        help_text='Total calculado automaticamente baseado na seleção de serviços'
    )
    
    # Campos para locais de entrega/devolução
    pickup_location_choice = forms.ModelChoiceField(
        queryset=DeliveryLocation.objects.filter(
            is_active=True,
            location_type__in=['pickup', 'both']
        ).order_by('name'),
        required=False,
        label='Local de Entrega (Predefinido)',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Selecione um local predefinido ou digite um personalizado abaixo'
    )
    
    return_location_choice = forms.ModelChoiceField(
        queryset=DeliveryLocation.objects.filter(
            is_active=True,
            location_type__in=['return', 'both']
        ).order_by('name'),
        required=False,
        label='Local de Devolução (Predefinido)',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Selecione um local predefinido ou digite um personalizado abaixo'
    )
    
    class Meta:
        model = Rental
        fields = [
            'vehicle', 'customer', 'start_date', 'end_date',
            'daily_rate', 'commission_percent', 'commission_amount', 'insurance_fee', 'security_deposit',
            'mileage_start', 'fuel_level_start', 'driver', 'car_seat', 
            'pickup_location', 'return_location', 'notes'
        ]
        labels = {
            'vehicle': 'Veículo',
            'customer': 'Cliente',
            'start_date': 'Data de Início',
            'end_date': 'Data de Fim',
            'daily_rate': 'Tarifa Diária',
            'commission_percent': 'Taxa de Comissão (%)',
            'commission_amount': 'Taxa de Comissão (ECV)',
            'insurance_fee': 'Taxa de Seguro',
            'security_deposit': 'Depósito de Segurança',
            'mileage_start': 'Quilometragem Inicial',
            'fuel_level_start': 'Nível de Combustível Inicial',
            'driver': 'Necessita de Motorista (+3.000 ECV/dia)',
            'car_seat': 'Necessita de Assento de Criança (+500 ECV/dia)',
            'pickup_location': 'Local de Entrega',
            'return_location': 'Local de Devolução',
            'notes': 'Notas'
        }
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'daily_rate': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'class': 'form-control'}),
            'commission_percent': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'max': '100', 'class': 'form-control', 'placeholder': 'Deixe vazio se usar valor fixo'}),
            'commission_amount': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'class': 'form-control', 'placeholder': 'Deixe vazio se usar percentagem'}),
            'insurance_fee': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'class': 'form-control'}),
            'security_deposit': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'class': 'form-control'}),
            'mileage_start': forms.NumberInput(attrs={'min': '0', 'class': 'form-control'}),
            'fuel_level_start': forms.Select(attrs={'class': 'form-control'}),
            'driver': forms.CheckboxInput(attrs={'class': 'form-check-input', 'data-driver-fee': '3000'}),
            'car_seat': forms.CheckboxInput(attrs={'class': 'form-check-input', 'data-seat-fee': '500'}),
            'pickup_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Aeroporto Amílcar Cabral, Hotel, Endereço... (ou deixe vazio se usar predefinido)'}),
            'return_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Aeroporto Amílcar Cabral, Hotel, Endereço... (ou deixe vazio se usar predefinido)'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'vehicle': forms.Select(attrs={'class': 'form-control'}),
            'customer': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract vehicle_id and customer_id from initial data if provided
        vehicle_id = kwargs.get('initial', {}).get('vehicle')
        customer_id = kwargs.get('initial', {}).get('customer')
        super().__init__(*args, **kwargs)
        
        # Show all active vehicles for both creating and editing
        # Date availability will be validated separately
        self.fields['vehicle'].queryset = Vehicle.objects.filter(is_active=True)
        
        # If vehicle_id is provided, set it as initial value
        if vehicle_id:
            try:
                vehicle = Vehicle.objects.get(pk=vehicle_id)
                self.fields['vehicle'].initial = vehicle
                # Pre-populate daily rate from vehicle
                if vehicle.daily_rate:
                    self.fields['daily_rate'].initial = vehicle.daily_rate
            except Vehicle.DoesNotExist:
                pass
        
        # If customer_id is provided, set it as initial value
        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
                self.fields['customer'].initial = customer
            except Customer.DoesNotExist:
                pass
        
        # Only show customers who can rent
        self.fields['customer'].queryset = Customer.objects.filter(is_blacklisted=False)
        
        # Make commission fields optional - validation will ensure one is provided
        self.fields['commission_percent'].required = False
        self.fields['commission_amount'].required = False
        
        # Make insurance_fee optional
        self.fields['insurance_fee'].required = False
    
    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date:
            # If it's a date, convert to datetime at start of day
            if not hasattr(start_date, 'hour'):
                from datetime import datetime, time
                start_date = datetime.combine(start_date, time.min)
            
            # Make timezone-aware if it's not
            if start_date.tzinfo is None:
                start_date = timezone.make_aware(start_date)

            # Start date cannot be before today (only for new rentals)
            if not self.instance.pk:
                today_start = timezone.make_aware(
                    __import__('datetime').datetime.combine(timezone.now().date(), __import__('datetime').time.min)
                )
                if start_date < today_start:
                    raise ValidationError('A data de início não pode ser inferior à data de hoje.')
        return start_date
    
    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')
        if end_date:
            # If it's a date, convert to datetime at end of day
            if not hasattr(end_date, 'hour'):
                from datetime import datetime, time
                end_date = datetime.combine(end_date, time(23, 59, 59))
            
            # Make timezone-aware if it's not
            if end_date.tzinfo is None:
                end_date = timezone.make_aware(end_date)

            # End date must be after today (only for new rentals)
            if not self.instance.pk:
                today_start = timezone.make_aware(
                    __import__('datetime').datetime.combine(timezone.now().date(), __import__('datetime').time.min)
                )
                if end_date < today_start:
                    raise ValidationError('A data de fim deve ser superior à data de hoje.')
        return end_date
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        vehicle = cleaned_data.get('vehicle')
        commission_percent = cleaned_data.get('commission_percent')
        commission_amount = cleaned_data.get('commission_amount')
        
        # Validate commission fields - exactly one should be used
        if commission_percent is not None and commission_amount is not None:
            raise ValidationError('Use percentagem de comissão OU valor fixo, não ambos.')
        elif commission_percent is None and commission_amount is None:
            raise ValidationError('Deve especificar a percentagem de comissão OU o valor fixo.')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError('A data de fim deve ser posterior à data de início.')
            
            # Allow start dates in the past - removed restriction for flexibility
            # This allows creating rentals for historical data or backdated entries
        
        if vehicle and start_date and end_date:
            # Use the new date-based availability check
            if not vehicle.is_available_for_dates(start_date, end_date):
                # If editing existing rental, exclude this rental from overlap check
                if self.instance and self.instance.pk:
                    overlapping_rentals = Rental.objects.filter(
                        vehicle=vehicle,
                        status__in=['confirmed', 'active'],
                        start_date__lt=end_date,
                        end_date__gt=start_date
                    ).exclude(pk=self.instance.pk)
                    
                    if overlapping_rentals.exists():
                        raise ValidationError('O veículo não está disponível para as datas selecionadas.')
                else:
                    # New rental - vehicle not available for these dates
                    raise ValidationError('O veículo não está disponível para as datas selecionadas.')
        
        return cleaned_data
    
    def clean_mileage_start(self):
        mileage_start = self.cleaned_data['mileage_start']
        vehicle = self.cleaned_data.get('vehicle')
        
        if vehicle and mileage_start < vehicle.mileage:
            raise ValidationError(f'A quilometragem inicial não pode ser inferior à quilometragem atual do veículo ({vehicle.mileage} km).')
        
        return mileage_start
    
    def save(self, commit=True):
        rental = super().save(commit=False)
        
        # Calculate rental duration and pricing
        if rental.start_date and rental.end_date:
            # Calculate number of days (minimum 1 day)
            duration = rental.end_date - rental.start_date
            rental.number_of_days = max(1, duration.days)
            
            # Calculate additional service fees
            rental.driver_fee = 3000 * rental.number_of_days if rental.driver else 0
            rental.car_seat_fee = 500 * rental.number_of_days if rental.car_seat else 0
            
            # Calculate subtotal
            rental.subtotal = rental.daily_rate * rental.number_of_days
            
            # Calculate commission amount based on either percentage or fixed amount
            if rental.commission_percent and rental.commission_percent > 0:
                # Use percentage-based commission
                rental.commission_amount = rental.subtotal * (rental.commission_percent / 100)
            elif rental.commission_amount and rental.commission_amount > 0:
                # Use fixed amount commission (already set)
                pass
            else:
                # No commission
                rental.commission_amount = 0
            
            # Calculate total amount - commission reduces the subtotal, then add additional fees
            rental.total_amount = (
                rental.subtotal - 
                rental.commission_amount + 
                (rental.insurance_fee or 0) + 
                (rental.security_deposit or 0) +
                rental.driver_fee +
                rental.car_seat_fee
            )
        
        if commit:
            rental.save()
        
        return rental


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'vehicle', 'category', 'rental', 'date', 'description',
            'amount', 'receipt_number', 'vendor'
        ]
        labels = {
            'vehicle': 'Veículo',
            'category': 'Categoria',
            'rental': 'Aluguer',
            'date': 'Data',
            'description': 'Descrição',
            'amount': 'Valor',
            'receipt_number': 'Número do Recibo',
            'vendor': 'Fornecedor'
        }
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'rental': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'step': 'any', 'min': '0.01', 'class': 'form-control'}),
            'receipt_number': forms.TextInput(attrs={'class': 'form-control'}),
            'vendor': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract vehicle_id from initial data if provided
        vehicle_id = kwargs.get('initial', {}).get('vehicle')
        super().__init__(*args, **kwargs)
        
        # Make rental field optional and filter by vehicle if provided
        self.fields['rental'].required = False
        
        # If vehicle_id is provided, set it as initial value and filter rentals
        if vehicle_id:
            try:
                from .models import Vehicle
                vehicle = Vehicle.objects.get(pk=vehicle_id)
                self.fields['vehicle'].initial = vehicle
                self.fields['rental'].queryset = Rental.objects.filter(vehicle_id=vehicle_id)
            except Vehicle.DoesNotExist:
                pass
        elif 'vehicle' in self.data:
            try:
                vehicle_id = int(self.data.get('vehicle'))
                self.fields['rental'].queryset = Rental.objects.filter(vehicle_id=vehicle_id)
            except (ValueError, TypeError):
                self.fields['rental'].queryset = Rental.objects.none()
        else:
            self.fields['rental'].queryset = Rental.objects.all()


class MaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRecord
        fields = [
            'vehicle', 'maintenance_type', 'date_scheduled', 'date_completed',
            'mileage', 'service_description', 'parts_replaced', 'service_provider',
            'labor_cost', 'parts_cost', 'other_costs', 'invoice_number',
            'warranty_until', 'status', 'notes', 'next_service_mileage', 'next_service_date'
        ]
        labels = {
            'vehicle': 'Veículo',
            'maintenance_type': 'Tipo de Manutenção',
            'date_scheduled': 'Data Agendada',
            'date_completed': 'Data de Conclusão',
            'mileage': 'Quilometragem',
            'service_description': 'Descrição do Serviço',
            'parts_replaced': 'Peças Substituídas',
            'service_provider': 'Prestador de Serviço',
            'labor_cost': 'Custo da Mão-de-Obra',
            'parts_cost': 'Custo das Peças',
            'other_costs': 'Outros Custos',
            'invoice_number': 'Número da Fatura',
            'warranty_until': 'Garantia Até',
            'status': 'Estado',
            'notes': 'Notas',
            'next_service_mileage': 'Próxima Revisão (Km)',
            'next_service_date': 'Próxima Revisão (Data)'
        }
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-control'}),
            'maintenance_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'date_scheduled': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_completed': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'warranty_until': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'next_service_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'labor_cost': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'class': 'form-control'}),
            'parts_cost': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'class': 'form-control'}),
            'other_costs': forms.NumberInput(attrs={'step': 'any', 'min': '0', 'class': 'form-control'}),
            'mileage': forms.NumberInput(attrs={'min': '0', 'class': 'form-control'}),
            'next_service_mileage': forms.NumberInput(attrs={'min': '0', 'class': 'form-control'}),
            'service_provider': forms.TextInput(attrs={'class': 'form-control'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'service_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'parts_replaced': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract vehicle_id from initial data if provided
        vehicle_id = kwargs.get('initial', {}).get('vehicle')
        super().__init__(*args, **kwargs)
        
        # Set default values for cost fields to make them optional
        self.fields['labor_cost'].initial = 0
        self.fields['parts_cost'].initial = 0
        self.fields['other_costs'].initial = 0
        
        # Make cost fields not required (they have default value of 0)
        self.fields['labor_cost'].required = False
        self.fields['parts_cost'].required = False
        self.fields['other_costs'].required = False
        
        # If vehicle_id is provided, set it as initial value
        if vehicle_id:
            try:
                from .models import Vehicle
                vehicle = Vehicle.objects.get(pk=vehicle_id)
                self.fields['vehicle'].initial = vehicle
            except Vehicle.DoesNotExist:
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        date_scheduled = cleaned_data.get('date_scheduled')
        date_completed = cleaned_data.get('date_completed')
        
        if date_completed and date_scheduled and date_completed < date_scheduled:
            raise ValidationError('A data de conclusão não pode ser anterior à data agendada.')
        
        return cleaned_data
    
    def clean_mileage(self):
        mileage = self.cleaned_data['mileage']
        vehicle = self.cleaned_data.get('vehicle')
        
        if vehicle and mileage < vehicle.mileage:
            raise ValidationError(f'A quilometragem de manutenção não pode ser inferior à quilometragem atual do veículo ({vehicle.mileage} km).')
        
        return mileage


# Quick forms for modals and AJAX
class QuickVehicleStatusForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['status']
        labels = {
            'status': 'Estado'
        }


class QuickRentalStatusForm(forms.ModelForm):
    class Meta:
        model = Rental
        fields = ['status']
        labels = {
            'status': 'Estado'
        }
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class QuickExpenseApprovalForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['is_approved']
        labels = {
            'is_approved': 'Aprovado'
        }


class RentalPhotoForm(forms.ModelForm):
    """Form for uploading rental photos"""
    class Meta:
        model = RentalPhoto
        fields = ['photo_type', 'image', 'description']
        labels = {
            'photo_type': 'Tipo de Foto',
            'image': 'Imagem',
            'description': 'Descrição (Opcional)'
        }
        widgets = {
            'photo_type': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'capture': 'camera'  # Enables camera capture on mobile devices
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Adicione detalhes específicos sobre a foto...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        rental = kwargs.pop('rental', None)
        photo_stage = kwargs.pop('photo_stage', 'start')  # 'start' or 'return'
        super().__init__(*args, **kwargs)
        
        # Filter photo type choices based on stage
        if photo_stage == 'start':
            start_choices = [choice for choice in RentalPhoto.PHOTO_TYPE_CHOICES if choice[0].startswith('start_')]
            self.fields['photo_type'].choices = start_choices
        elif photo_stage == 'return':
            return_choices = [choice for choice in RentalPhoto.PHOTO_TYPE_CHOICES if choice[0].startswith('return_')]
            self.fields['photo_type'].choices = return_choices


class RentalStartPhotosFormSet(forms.BaseInlineFormSet):
    """Custom formset for rental start photos"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default photo types for start photos
        if not self.data:
            required_start_photos = [
                'start_exterior_front',
                'start_exterior_back', 
                'start_exterior_left',
                'start_exterior_right',
                'start_dashboard'
            ]
            for i, photo_type in enumerate(required_start_photos):
                if i < len(self.forms):
                    self.forms[i].initial['photo_type'] = photo_type


class RentalReturnPhotosFormSet(forms.BaseInlineFormSet):
    """Custom formset for rental return photos"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default photo types for return photos
        if not self.data:
            required_return_photos = [
                'return_exterior_front',
                'return_exterior_back',
                'return_exterior_left', 
                'return_exterior_right',
                'return_dashboard',
                'return_fuel_gauge'
            ]
            for i, photo_type in enumerate(required_return_photos):
                if i < len(self.forms):
                    self.forms[i].initial['photo_type'] = photo_type


# Create formsets for rental photos
RentalStartPhotosFormSet = forms.inlineformset_factory(
    Rental, 
    RentalPhoto,
    form=RentalPhotoForm,
    formset=RentalStartPhotosFormSet,
    extra=5,  # Number of extra forms
    max_num=10  # Maximum number of photos
)

RentalReturnPhotosFormSet = forms.inlineformset_factory(
    Rental,
    RentalPhoto, 
    form=RentalPhotoForm,
    formset=RentalReturnPhotosFormSet,
    extra=6,  # Number of extra forms
    max_num=10  # Maximum number of photos
)


class VehicleBrandForm(forms.ModelForm):
    class Meta:
        model = VehicleBrand
        fields = ['name', 'country_of_origin']
        labels = {
            'name': 'Nome da Marca',
            'country_of_origin': 'País de Origem',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Toyota, BMW...'}),
            'country_of_origin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Japão, Alemanha...'}),
        }


class DeliveryLocationForm(forms.ModelForm):
    class Meta:
        model = DeliveryLocation
        fields = ['name', 'address', 'location_type', 'description', 'is_active', 'default_pickup', 'default_return']
        labels = {
            'name': 'Nome do Local',
            'address': 'Endereço',
            'location_type': 'Tipo de Local',
            'description': 'Descrição',
            'is_active': 'Ativo',
            'default_pickup': 'Local Padrão de Entrega',
            'default_return': 'Local Padrão de Devolução',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'location_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_pickup': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_return': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description', 'is_active']
        labels = {
            'name': 'Nome da Categoria',
            'description': 'Descrição',
            'is_active': 'Ativa',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SystemConfigurationForm(forms.ModelForm):
    class Meta:
        model = SystemConfiguration
        fields = [
            'service_fee_percentage', 'service_fee_amount',
            'driver_daily_rate', 'car_seat_daily_rate',
            'euro_exchange_rate', 'usd_exchange_rate',
        ]
        labels = {
            'service_fee_percentage': 'Taxa de Serviço (%)',
            'service_fee_amount': 'Taxa de Serviço (Valor Fixo)',
            'driver_daily_rate': 'Tarifa Diária Motorista (CVE)',
            'car_seat_daily_rate': 'Tarifa Diária Assento Criança (CVE)',
            'euro_exchange_rate': 'Taxa de Câmbio EUR/CVE',
            'usd_exchange_rate': 'Taxa de Câmbio USD/CVE',
        }
        widgets = {
            'service_fee_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'service_fee_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'driver_daily_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'car_seat_daily_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'euro_exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'usd_exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
        }

# User Management Forms
class UserCreateForm(forms.ModelForm):
    """Form for creating a new user"""
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'})
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {
            'username': 'Nome de Utilizador',
            'first_name': 'Primeiro Nome',
            'last_name': 'Último Nome',
            'email': 'Email',
            'is_active': 'Ativo',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome de utilizador'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primeiro nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Último nome'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('As palavras-passe não coincidem.')
        return password2
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError('Este email já está registado.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_staff = True  # Always set as staff
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserEditForm(forms.ModelForm):
    """Form for editing an existing user"""
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {
            'username': 'Nome de Utilizador',
            'first_name': 'Primeiro Nome',
            'last_name': 'Último Nome',
            'email': 'Email',
            'is_active': 'Ativo',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome de utilizador', 'readonly': 'readonly'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primeiro nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Último nome'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Este email já está registado.')
        return email


class UserPasswordChangeForm(forms.Form):
    """Form for changing a user'\''s password"""
    new_password1 = forms.CharField(
        label='Nova Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'})
    )
    new_password2 = forms.CharField(
        label='Confirmar Nova Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'})
    )
    
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('As palavras-passe não coincidem.')
        return password2


class UserPermissionsForm(forms.ModelForm):
    """Form for managing user permissions"""
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Permissões'
    )
    
    class Meta:
        model = User
        fields = ['user_permissions']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Organize permissions by content type for better display
        vehicle_rental_ct = ContentType.objects.filter(app_label='vehicle_rental')
        self.fields['user_permissions'].queryset = Permission.objects.filter(
            content_type__in=vehicle_rental_ct
        ).select_related('content_type').order_by('content_type__model', 'codename')
