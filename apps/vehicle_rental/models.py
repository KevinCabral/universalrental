from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import os
import uuid


def vehicle_photo_upload_path(instance, filename):
    """Generate upload path for vehicle photos"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('vehicle_photos', str(instance.id or 'temp'), filename)


class DeliveryLocation(models.Model):
    """Delivery and return locations for rentals"""
    
    LOCATION_TYPE_CHOICES = [
        ('pickup', _('Local de Entrega')),
        ('return', _('Local de Devolução')),
        ('both', _('Entrega e Devolução')),
    ]
    
    name = models.CharField(
        max_length=200,
        help_text=_("Nome do local (ex: Aeroporto Amílcar Cabral, Hotel Pestana, etc.)")
    )
    address = models.TextField(
        blank=True,
        null=True,
        help_text=_("Endereço completo do local")
    )
    location_type = models.CharField(
        max_length=20,
        choices=LOCATION_TYPE_CHOICES,
        default='both',
        help_text=_("Tipo de operação no local")
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text=_("Informações adicionais sobre o local")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Local ativo para uso")
    )
    default_pickup = models.BooleanField(
        default=False,
        help_text=_("Local padrão para entrega")
    )
    default_return = models.BooleanField(
        default=False,
        help_text=_("Local padrão para devolução")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_locations'
    )
    
    class Meta:
        verbose_name = _("Local de Entrega/Devolução")
        verbose_name_plural = _("Locais de Entrega/Devolução")
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['location_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"
    
    def clean(self):
        # Ensure only one default pickup and one default return location
        if self.default_pickup:
            DeliveryLocation.objects.filter(
                default_pickup=True,
                location_type__in=['pickup', 'both']
            ).exclude(pk=self.pk).update(default_pickup=False)
        
        if self.default_return:
            DeliveryLocation.objects.filter(
                default_return=True,
                location_type__in=['return', 'both']
            ).exclude(pk=self.pk).update(default_return=False)


class VehicleBrand(models.Model):
    """Vehicle brand lookup table"""
    name = models.CharField(max_length=100, unique=True)
    country_of_origin = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Vehicle Brand")
        verbose_name_plural = _("Vehicle Brands")
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Vehicle(models.Model):
    """Enhanced Vehicle model with proper relationships and validation"""
    
    FUEL_CHOICES = [
        ('petrol', _('Gasóleo')),
        ('diesel', _('Diesel')),
        ('electric', _('Eléctrico')),
        ('hybrid', _('Híbrido')),
        ('lpg', _('GPL')),
        ('gas', _('Gasolina')),
    ]
    
    GEARBOX_CHOICES = [
        ('manual', _('Manual')),
        ('automatic', _('Automática')),
        ('cvt', _('CVT')),
        ('semi_automatic', _('Semi-Automática')),
    ]
    
    STATUS_CHOICES = [
        ('available', _('Disponível')),
        ('rented', _('Alugado')),
        ('maintenance', _('Em Manutenção')),
        ('retired', _('Retirado')),
    ]
    
    # Basic Information
    brand = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE, related_name='vehicles')
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2030)]
    )
    description = models.TextField(
        blank=True, null=True,
        help_text=_("Additional description or notes about the vehicle")
    )
    
    # Identification
    chassis_number = models.CharField(
        max_length=50, 
        unique=True,
        null=True, blank=True,
        help_text=_("Vehicle Identification Number (VIN)")
    )
    registration_number = models.CharField(
        max_length=20, 
        unique=True,
        help_text=_("License plate number")
    )
    
    # Physical Characteristics
    color = models.CharField(max_length=50)
    photo = models.ImageField(
        upload_to=vehicle_photo_upload_path,
        null=True, blank=True,
        help_text=_("Vehicle photo (optional)")
    )
    engine_size = models.PositiveIntegerField(
        help_text=_("Engine size in cubic centimeters (cc)"),
        null=True, blank=True
    )
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES)
    gearbox_type = models.CharField(max_length=20, choices=GEARBOX_CHOICES)
    
    # Features
    panoramic_roof = models.BooleanField(default=False)
    air_conditioning = models.BooleanField(default=True)
    number_of_seats = models.PositiveIntegerField(default=5)
    
    # Operational Data
    mileage = models.PositiveIntegerField(
        default=0,
        help_text=_("Current mileage in kilometers")
    )
    purchase_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date_of_purchase = models.DateField(null=True, blank=True)
    
    # Daily rental rate
    daily_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text=_("Daily rental rate")
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = _("Vehicle")
        verbose_name_plural = _("Vehicles")
        ordering = ['brand__name', 'model', 'year']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['registration_number']),
            models.Index(fields=['chassis_number']),
        ]
    
    def __str__(self):
        return f"{self.brand.name} {self.model} ({self.year}) - {self.registration_number}"
    
    @property
    def is_available(self):
        return self.status == 'available' and self.is_active
    
    def get_current_rental(self):
        """Get current active rental for this vehicle"""
        return self.rentals.filter(
            status='active',
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).first()
    
    def is_available_for_dates(self, start_date, end_date):
        """Check if vehicle is available for specific date range"""
        # Vehicle must be active and not in permanent maintenance/retired
        if not self.is_active or self.status in ['retired']:
            return False
        
        # Check for overlapping confirmed or active rentals
        overlapping_rentals = self.rentals.filter(
            status__in=['confirmed', 'active'],
            start_date__lt=end_date,
            end_date__gt=start_date
        ).exists()
        
        # Check for overlapping maintenance periods
        # Import locally to avoid circular imports
        overlapping_maintenance = MaintenanceRecord.objects.filter(
            vehicle=self,
            status__in=['scheduled', 'in_progress'],
            date_scheduled__lt=end_date.date() if hasattr(end_date, 'date') else end_date,
            date_completed__isnull=True
        ).exists()
        
        return not overlapping_rentals and not overlapping_maintenance


class Customer(models.Model):
    """Customer model for rental management"""
    
    # User Account
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile', null=True, blank=True)
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    birth_date = models.DateField(
        help_text=_("Data de nascimento do cliente")
    )
    
    # Address
    address_line_1 = models.CharField(max_length=200, blank=True, null=True)
    address_line_2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default='Portugal')
    
    # Identification
    id_number = models.CharField(max_length=50, unique=True, help_text=_("National ID or Passport Number"))
    driving_license_number = models.CharField(max_length=50, unique=True)
    license_issue_date = models.DateField(
        help_text=_("Data de emissão da carta de condução")
    )
    license_expiry_date = models.DateField(null=True, blank=True)
    
    # Customer Status
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True, null=True)
    
    # OTP for Password Recovery
    otp = models.CharField(
        max_length=6,
        null=True,
        blank=True,
        help_text=_("One-time password for password recovery")
    )
    otp_created_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when OTP was created")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['id_number']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def can_rent(self):
        """Check if customer can rent a vehicle"""
        if self.is_blacklisted:
            return False
        if self.license_expiry_date < timezone.now().date():
            return False
        return True
    
    def is_otp_valid(self, expiry_minutes=15):
        """Check if OTP is still valid (not expired)"""
        if not self.otp or not self.otp_created_at:
            return False
        
        expiry_time = self.otp_created_at + timezone.timedelta(minutes=expiry_minutes)
        return timezone.now() <= expiry_time
    
    def clear_otp(self):
        """Clear the OTP after successful use or expiry"""
        self.otp = None
        self.otp_created_at = None
        self.save()


class Rental(models.Model):
    """Enhanced Rental model with proper relationships"""
    
    STATUS_CHOICES = [
        ('pending', _('Pendente')),
        ('confirmed', _('Confirmado')),
        ('active', _('Ativo')),
        ('completed', _('Concluído')),
        ('cancelled', _('Cancelado')),
    ]
    
    # Relationships
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='rentals')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='rentals')
    
    # Rental Period
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    actual_return_date = models.DateTimeField(null=True, blank=True)
    
    # Pricing
    daily_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text=_("Daily rate at time of booking")
    )
    number_of_days = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Commission and fees
    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    commission_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True,
        blank=True
    )
    
    # Additional charges
    insurance_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    late_return_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    damage_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Additional requirements
    driver = models.BooleanField(
        default=False,
        help_text=_("Necessita de motorista")
    )
    car_seat = models.BooleanField(
        default=False,
        help_text=_("Necessita de assento de criança")
    )
    
    # Additional fees for services
    driver_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text=_("Taxa adicional de motorista por dia (3000 ECV)")
    )
    car_seat_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text=_("Taxa adicional de assento criança por dia (500 ECV)")
    )
    
    # Pickup and return locations
    pickup_location = models.ForeignKey(
        'DeliveryLocation',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='pickup_rentals',
        help_text=_("Local de entrega do veículo")
    )
    return_location = models.ForeignKey(
        'DeliveryLocation',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='return_rentals',
        help_text=_("Local de devolução do veículo")
    )
    
    # Total
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Vehicle condition
    mileage_start = models.PositiveIntegerField()
    mileage_end = models.PositiveIntegerField(null=True, blank=True)
    fuel_level_start = models.CharField(
        max_length=20,
        choices=[('empty', 'Empty'), ('quarter', '1/4'), ('half', '1/2'), ('three_quarter', '3/4'), ('full', 'Full')],
        default='full'
    )
    fuel_level_end = models.CharField(
        max_length=20,
        choices=[('empty', 'Empty'), ('quarter', '1/4'), ('half', '1/2'), ('three_quarter', '3/4'), ('full', 'Full')],
        null=True, blank=True
    )
    
    # Status and notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = _("Rental")
        verbose_name_plural = _("Rentals")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
        ]
    
    def __str__(self):
        return f"Rental #{self.id} - {self.vehicle} ({self.customer})"
    
    def save(self, *args, **kwargs):
        # Calculate number of days
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            self.number_of_days = max(1, delta.days)
        
        # Calculate amounts
        if self.daily_rate and self.number_of_days:
            base_amount = self.daily_rate * self.number_of_days
            
            # Calculate additional service fees
            self.driver_fee = Decimal('3000') * self.number_of_days if self.driver else Decimal('0')
            self.car_seat_fee = Decimal('500') * self.number_of_days if self.car_seat else Decimal('0')
            
            # Calculate commission amount based on either percentage or fixed amount
            commission = 0
            if self.commission_percent is not None:
                # Use percentage-based commission (including 0%)
                commission = (base_amount * self.commission_percent) / 100
                self.commission_amount = None  # Clear the fixed amount
            elif self.commission_amount is not None:
                # Use fixed amount commission (including 0)
                commission = self.commission_amount
                self.commission_percent = None  # Clear the percentage
            else:
                # No commission fields set - clear both fields
                self.commission_percent = None
                self.commission_amount = None
                
            # Subtotal is base amount minus commission
            self.subtotal = base_amount - commission
            
            # Total amount includes additional fees
            self.total_amount = (
                self.subtotal + 
                (self.insurance_fee or 0) + 
                (self.late_return_fee or 0) + 
                (self.damage_fee or 0) +
                self.driver_fee +
                self.car_seat_fee
            )
        
        super().save(*args, **kwargs)
    
    @property
    def base_amount(self):
        """Calculate the base amount (days × daily_rate) before commission"""
        if self.daily_rate and self.number_of_days:
            return self.daily_rate * self.number_of_days
        return 0
    
    @property
    def commission_value(self):
        """Calculate the actual commission value"""
        if self.commission_percent is not None:
            return (self.base_amount * self.commission_percent) / 100
        elif self.commission_amount is not None:
            return self.commission_amount
        return 0
    
    @property
    def is_overdue(self):
        if self.status == 'active' and self.end_date:
            return timezone.now() > self.end_date
        return False
    
    @property
    def days_overdue(self):
        if self.is_overdue:
            return (timezone.now() - self.end_date).days
        return 0
    
    @property
    def get_rental_duration(self):
        """Return the rental duration in days"""
        return self.number_of_days if self.number_of_days else 0
    
    @property
    def is_returned(self):
        """Check if the rental has been returned"""
        return self.actual_return_date is not None


class RentalEvaluation(models.Model):
    """Customer evaluation/review of completed rental"""
    
    RATING_CHOICES = [
        (1, '1 - Muito Insatisfeito'),
        (2, '2 - Insatisfeito'),
        (3, '3 - Neutro'),
        (4, '4 - Satisfeito'),
        (5, '5 - Muito Satisfeito'),
    ]
    
    # Relationships
    rental = models.OneToOneField(
        Rental, 
        on_delete=models.CASCADE, 
        related_name='evaluation',
        help_text=_("Rental being evaluated")
    )
    
    # Overall Rating
    overall_rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        help_text=_("Overall satisfaction rating (1-5)")
    )
    
    # Specific Ratings
    vehicle_condition_rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        help_text=_("Vehicle condition rating (1-5)")
    )
    
    service_quality_rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        help_text=_("Service quality rating (1-5)")
    )
    
    value_for_money_rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        help_text=_("Value for money rating (1-5)")
    )
    
    # Written Feedback
    comments = models.TextField(
        blank=True, null=True,
        help_text=_("Additional comments and feedback")
    )
    
    # Recommendation
    would_recommend = models.BooleanField(
        default=True,
        help_text=_("Would the customer recommend this service?")
    )
    
    # Issues/Complaints
    had_issues = models.BooleanField(
        default=False,
        help_text=_("Did the customer experience any issues?")
    )
    
    issue_description = models.TextField(
        blank=True, null=True,
        help_text=_("Description of any issues experienced")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Rental Evaluation")
        verbose_name_plural = _("Rental Evaluations")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['overall_rating']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Evaluation for Rental #{self.rental.id} - {self.overall_rating}/5 stars"
    
    @property
    def average_rating(self):
        """Calculate average of all specific ratings"""
        ratings = [
            self.overall_rating,
            self.vehicle_condition_rating,
            self.service_quality_rating,
            self.value_for_money_rating
        ]
        return sum(ratings) / len(ratings)
    
    @property
    def rating_stars(self):
        """Return star representation of overall rating"""
        return "★" * self.overall_rating + "☆" * (5 - self.overall_rating)


class ExpenseCategory(models.Model):
    """Expense category lookup table"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _("Expense Category")
        verbose_name_plural = _("Expense Categories")
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Expense(models.Model):
    """Enhanced Expense model with proper categorization"""
    
    # Relationships
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='expenses')
    rental = models.ForeignKey(
        Rental, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='expenses',
        help_text=_("Link to rental if expense is rental-specific")
    )
    
    # Expense Details
    date = models.DateField(default=timezone.now)
    description = models.TextField(help_text=_("Detailed description of the expense"))
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Documentation
    receipt_number = models.CharField(max_length=100, blank=True, null=True)
    vendor = models.CharField(max_length=200, blank=True, null=True)
    
    # Approval
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_expenses'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = _("Expense")
        verbose_name_plural = _("Expenses")
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['category']),
            models.Index(fields=['is_approved']),
        ]
    
    def __str__(self):
        return f"{self.category.name} - {self.vehicle} - ${self.amount}"


class MaintenanceRecord(models.Model):
    """Enhanced Maintenance Record model"""
    
    MAINTENANCE_TYPES = [
        ('scheduled', _('Manutenção Programada')),
        ('repair', _('Reparação')),
        ('inspection', _('Inspeção')),
        ('warranty', _('Trabalho de Garantia')),
        ('accident', _('Reparação de Acidente')),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', _('Agendado')),
        ('in_progress', _('Em Progresso')),
        ('completed', _('Concluído')),
        ('cancelled', _('Cancelado')),
    ]
    
    # Relationships
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='maintenance_records')
    
    # Maintenance Details
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPES)
    date_scheduled = models.DateField()
    date_completed = models.DateField(null=True, blank=True)
    
    # Vehicle condition
    mileage = models.PositiveIntegerField(help_text=_("Vehicle mileage at time of maintenance"))
    
    # Service details
    service_description = models.TextField()
    parts_replaced = models.TextField(blank=True, null=True)
    service_provider = models.CharField(max_length=200)
    
    # Cost breakdown
    labor_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    parts_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    other_costs = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Documentation
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    warranty_until = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True, null=True)
    
    # Next maintenance
    next_service_mileage = models.PositiveIntegerField(null=True, blank=True)
    next_service_date = models.DateField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = _("Maintenance Record")
        verbose_name_plural = _("Maintenance Records")
        ordering = ['-date_scheduled']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['date_scheduled']),
            models.Index(fields=['maintenance_type']),
        ]
    
    def __str__(self):
        return f"{self.maintenance_type.title()} - {self.vehicle} ({self.date_scheduled})"
    
    def get_total_cost(self):
        """Calculate and return total cost"""
        return (self.labor_cost or 0) + (self.parts_cost or 0) + (self.other_costs or 0)
    
    def save(self, *args, **kwargs):
        # Calculate total cost
        self.total_cost = self.get_total_cost()
        super().save(*args, **kwargs)


def rental_photo_upload_path(instance, filename):
    """Generate upload path for rental photos"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('rental_photos', str(instance.rental.id), instance.photo_type, filename)


class RentalPhoto(models.Model):
    """Photos taken during rental process (start and return)"""
    
    PHOTO_TYPE_CHOICES = [
        ('start_exterior_front', _('Inicial - Exterior Frente')),
        ('start_exterior_back', _('Inicial - Exterior Traseira')),
        ('start_exterior_left', _('Inicial - Exterior Esquerda')),
        ('start_exterior_right', _('Inicial - Exterior Direita')),
        ('start_interior_front', _('Inicial - Interior Frente')),
        ('start_interior_back', _('Inicial - Interior Traseira')),
        ('start_dashboard', _('Inicial - Painel')),
        ('start_damage', _('Inicial - Danos Existentes')),
        ('return_exterior_front', _('Devolução - Exterior Frente')),
        ('return_exterior_back', _('Devolução - Exterior Traseira')),
        ('return_exterior_left', _('Devolução - Exterior Esquerda')),
        ('return_exterior_right', _('Devolução - Exterior Direita')),
        ('return_interior_front', _('Devolução - Interior Frente')),
        ('return_interior_back', _('Devolução - Interior Traseira')),
        ('return_dashboard', _('Devolução - Painel')),
        ('return_damage', _('Devolução - Novos Danos')),
        ('return_fuel_gauge', _('Devolução - Medidor Combustível')),
    ]
    
    rental = models.ForeignKey(Rental, on_delete=models.CASCADE, related_name='photos')
    photo_type = models.CharField(max_length=30, choices=PHOTO_TYPE_CHOICES)
    image = models.ImageField(upload_to=rental_photo_upload_path)
    description = models.TextField(blank=True, null=True, help_text=_("Opcional: Descreva detalhes específicos"))
    taken_at = models.DateTimeField(auto_now_add=True)
    taken_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Optional GPS coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    class Meta:
        verbose_name = _("Rental Photo")
        verbose_name_plural = _("Rental Photos")
        ordering = ['taken_at']
        unique_together = ['rental', 'photo_type']  # Only one photo per type per rental
        indexes = [
            models.Index(fields=['rental']),
            models.Index(fields=['photo_type']),
            models.Index(fields=['taken_at']),
        ]
    
    def __str__(self):
        return f"Photo - {self.get_photo_type_display()} (Rental #{self.rental.id})"
    
    @property
    def is_start_photo(self):
        """Check if this is a start photo"""
        return self.photo_type.startswith('start_')
    
    @property
    def is_return_photo(self):
        """Check if this is a return photo"""
        return self.photo_type.startswith('return_')
    
    def delete(self, *args, **kwargs):
        """Delete the image file from storage when model is deleted"""
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)


def vehicle_additional_photo_upload_path(instance, filename):
    """Generate upload path for additional vehicle photos"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('vehicle_photos', str(instance.vehicle.id), 'additional', filename)


class VehiclePhoto(models.Model):
    """Additional photos for vehicles"""
    
    PHOTO_TYPE_CHOICES = [
        ('exterior_front', _('Exterior - Front')),
        ('exterior_back', _('Exterior - Back')),
        ('exterior_left', _('Exterior - Left Side')),
        ('exterior_right', _('Exterior - Right Side')),
        ('interior_dashboard', _('Interior - Dashboard')),
        ('interior_seats', _('Interior - Seats')),
        ('interior_trunk', _('Interior - Trunk')),
        ('engine', _('Engine')),
        ('documents', _('Documents')),
        ('damage', _('Damage/Issue')),
        ('other', _('Other')),
    ]
    
    # Relationships
    vehicle = models.ForeignKey(
        Vehicle, 
        on_delete=models.CASCADE, 
        related_name='additional_photos',
        help_text=_("Vehicle this photo belongs to")
    )
    
    # Photo Information
    image = models.ImageField(
        upload_to=vehicle_additional_photo_upload_path,
        help_text=_("Vehicle photo")
    )
    photo_type = models.CharField(
        max_length=30, 
        choices=PHOTO_TYPE_CHOICES,
        default='other',
        help_text=_("Type/category of this photo")
    )
    title = models.CharField(
        max_length=200, 
        blank=True, null=True,
        help_text=_("Optional title or description for this photo")
    )
    description = models.TextField(
        blank=True, null=True,
        help_text=_("Optional detailed description")
    )
    
    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        help_text=_("User who uploaded this photo")
    )
    is_primary = models.BooleanField(
        default=False,
        help_text=_("Mark as primary photo for this vehicle")
    )
    
    class Meta:
        verbose_name = _("Vehicle Photo")
        verbose_name_plural = _("Vehicle Photos")
        ordering = ['-is_primary', 'photo_type', '-uploaded_at']
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['photo_type']),
            models.Index(fields=['is_primary']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def __str__(self):
        return f"Photo - {self.get_photo_type_display()} ({self.vehicle.registration_number})"
    
    def save(self, *args, **kwargs):
        # If this is marked as primary, unmark other primary photos for this vehicle
        if self.is_primary:
            VehiclePhoto.objects.filter(
                vehicle=self.vehicle, 
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Delete the image file from storage when model is deleted"""
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)
    
    @property
    def file_size(self):
        """Get file size in bytes"""
        if self.image and os.path.isfile(self.image.path):
            return os.path.getsize(self.image.path)
        return 0
    
    @property
    def file_size_human(self):
        """Get human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"



