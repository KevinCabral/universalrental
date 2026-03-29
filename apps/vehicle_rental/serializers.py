from rest_framework import serializers
from .models import (
    Vehicle, VehicleBrand, Customer, Rental, Expense, ExpenseCategory,
    MaintenanceRecord, RentalEvaluation, VehiclePhoto, DeliveryLocation, SystemConfiguration,
    CustomerNotification
)


class DeliveryLocationSerializer(serializers.ModelSerializer):
    location_type_display = serializers.CharField(source='get_location_type_display', read_only=True)
    
    class Meta:
        model = DeliveryLocation
        fields = [
            'id', 'name', 'address', 'location_type', 'location_type_display',
            'description', 'is_active', 'default_pickup', 'default_return'
        ]


class VehicleBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleBrand
        fields = ['id', 'name', 'country_of_origin']


class VehiclePhotoSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    file_size_human = serializers.ReadOnlyField()
    photo_type_display = serializers.CharField(source='get_photo_type_display', read_only=True)
    
    class Meta:
        model = VehiclePhoto
        fields = [
            'id', 'vehicle', 'image', 'photo_type', 'photo_type_display',
            'title', 'description', 'uploaded_at', 'uploaded_by', 
            'uploaded_by_name', 'is_primary', 'file_size_human'
        ]
        read_only_fields = ['uploaded_at', 'uploaded_by', 'uploaded_by_name', 'file_size_human']
    
    def create(self, validated_data):
        # Set the uploaded_by to the current user if available and authenticated
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['uploaded_by'] = request.user
        else:
            # If no authenticated user, set to None (which is allowed since the field is nullable)
            validated_data['uploaded_by'] = None
        return super().create(validated_data)


class VehicleSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    current_rental = serializers.SerializerMethodField()
    active_rentals = serializers.SerializerMethodField()
    additional_photos = VehiclePhotoSerializer(many=True, read_only=True)
    photos_count = serializers.SerializerMethodField()
    primary_photo = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'brand', 'brand_name', 'model', 'year', 'description', 'description_en', 'description_fr', 'chassis_number',
            'registration_number', 'color', 'photo', 'engine_size', 'fuel_type',
            'gearbox_type', 'panoramic_roof', 'air_conditioning', 'number_of_seats',
            'mileage', 'purchase_price', 'date_of_purchase', 'daily_rate',
            'status', 'is_active', 'is_available', 'current_rental', 'active_rentals',
            'additional_photos', 'photos_count', 'primary_photo', 'stats',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'additional_photos', 'photos_count', 'primary_photo', 'stats']
    
    def get_current_rental(self, obj):
        current_rental = obj.get_current_rental()
        if current_rental:
            return {
                'id': current_rental.id,
                'customer': current_rental.customer.full_name,
                'start_date': current_rental.start_date,
                'end_date': current_rental.end_date,
            }
        return None
    
    def get_active_rentals(self, obj):
        """Get list of rentals where end_date >= today"""
        from django.utils import timezone
        today = timezone.now().date()
        
        active_rentals = obj.rentals.filter(
            end_date__date__gte=today
        ).select_related('customer').order_by('start_date')
        
        return [
            {
                #'id': rental.id,
                #'customer': rental.customer.full_name,
                #'customer_email': rental.customer.email,
                'start_date': rental.start_date,
                'end_date': rental.end_date,
                'status': rental.status,
                'status_display': rental.get_status_display(),
                #'total_amount': rental.total_amount,
                #'daily_rate': rental.daily_rate,
            }
            for rental in active_rentals
        ]
    
    def get_photos_count(self, obj):
        """Get total number of additional photos"""
        return obj.additional_photos.count()
    
    def get_primary_photo(self, obj):
        """Get the primary photo if exists"""
        primary_photo = obj.additional_photos.filter(is_primary=True).first()
        if primary_photo:
            return VehiclePhotoSerializer(primary_photo, context=self.context).data
        return None

    def get_stats(self, obj):
        """Get evaluation statistics for the vehicle"""
        from django.db.models import Avg
        
        # Get all evaluations for this vehicle through rentals
        evaluations = RentalEvaluation.objects.filter(
            rental__vehicle=obj
        ).select_related('rental')
        
        total_evaluations = evaluations.count()
        
        if total_evaluations > 0:
            # Calculate average ratings
            avg_ratings = evaluations.aggregate(
                overall=Avg('overall_rating'),
                vehicle_condition=Avg('vehicle_condition_rating'),
                service_quality=Avg('service_quality_rating'),
                value_for_money=Avg('value_for_money_rating')
            )
            
            recommendations = evaluations.filter(would_recommend=True).count()
            issues_count = evaluations.filter(had_issues=True).count()
            
            stats = {
                'total_evaluations': total_evaluations,
                'average_overall_rating': round(avg_ratings['overall'] or 0, 2),
                'average_vehicle_condition': round(avg_ratings['vehicle_condition'] or 0, 2),
                'average_service_quality': round(avg_ratings['service_quality'] or 0, 2),
                'average_value_for_money': round(avg_ratings['value_for_money'] or 0, 2),
                'recommendation_percentage': round((recommendations / total_evaluations) * 100, 2) if total_evaluations > 0 else 0,
                'issues_percentage': round((issues_count / total_evaluations) * 100, 2) if total_evaluations > 0 else 0,
                'total_rentals_evaluated': total_evaluations
            }
        else:
            stats = {
                'total_evaluations': 0,
                'average_overall_rating': 0,
                'average_vehicle_condition': 0,
                'average_service_quality': 0,
                'average_value_for_money': 0,
                'recommendation_percentage': 0,
                'issues_percentage': 0,
                'total_rentals_evaluated': 0
            }
        
        return stats


class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    can_rent = serializers.BooleanField(read_only=True)
    rental_count = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    license_expiry_date = serializers.DateField(required=False)

    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email',
            'phone_number', 'birth_date', 'age', 'address_line_1', 'address_line_2', 'city',
            'postal_code', 'country', 'id_number', 'driving_license_number',
            'license_issue_date', 'license_expiry_date', 'is_blacklisted', 'blacklist_reason',
            'can_rent', 'rental_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_rental_count(self, obj):
        return obj.rentals.count()
    
    def get_age(self, obj):
        if obj.birth_date:
            from datetime import date
            today = date.today()
            return today.year - obj.birth_date.year - ((today.month, today.day) < (obj.birth_date.month, obj.birth_date.day))
        return None
    
    def validate_email(self, value):
        if value:
            existing_customer = Customer.objects.filter(email=value).exclude(pk=self.instance.pk if self.instance else None).first()
            if existing_customer:
                # Only raise error if customer already has a user account
                if existing_customer.user is not None:
                    raise serializers.ValidationError("Customer with this email already exists.")
        return value
    
    def validate_driving_license_number(self, value):
        if value:
            existing_customer = Customer.objects.filter(driving_license_number=value).exclude(pk=self.instance.pk if self.instance else None).first()
            if existing_customer:
                # Only raise error if customer already has a user account
                if existing_customer.user is not None:
                    raise serializers.ValidationError("Customer with this driving license number already exists.")
        return value


class RentalSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    vehicle_info = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Rental
        fields = [
            'id', 'vehicle', 'vehicle_info', 'customer', 'customer_name',
            'start_date', 'end_date', 'actual_return_date', 'currency', 'daily_rate',
            'number_of_days', 'subtotal', 'commission_percent', 'commission_amount',
            'insurance_fee', 'security_deposit', 'late_return_fee', 'damage_fee',
            'driver', 'car_seat', 'driver_fee', 'car_seat_fee',
            'pickup_location', 'return_location',
            'total_amount', 'amount_paid', 'mileage_start', 'mileage_end',
            'fuel_level_start', 'fuel_level_end',
            'status', 'notes', 'is_overdue', 'days_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'number_of_days', 'subtotal', 'commission_amount', 'driver_fee', 'car_seat_fee',
            'total_amount', 'created_at', 'updated_at', 'created_by'
        ]
    
    def get_vehicle_info(self, obj):
        return {
            'id': obj.vehicle.id,
            'registration_number': obj.vehicle.registration_number,
            'brand': obj.vehicle.brand.name,
            'model': obj.vehicle.model,
            'year': obj.vehicle.year,
        }
    
    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("End date must be after start date.")

        # Check vehicle availability
        vehicle = data['vehicle']
        start_date = data['start_date']
        end_date = data['end_date']
        
        overlapping_rentals = Rental.objects.filter(
            vehicle=vehicle,
            status__in=['confirmed', 'active', 'pending'],  # Consider pending rentals as well to prevent double booking
            start_date__lt=end_date,
            end_date__gt=start_date
        )
        
        if self.instance:
            overlapping_rentals = overlapping_rentals.exclude(pk=self.instance.pk)
        
        if overlapping_rentals.exists():
            raise serializers.ValidationError("Vehicle is not available for the selected dates.")
        
        return data


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'description', 'is_active']


class ExpenseSerializer(serializers.ModelSerializer):
    vehicle_info = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Expense
        fields = [
            'id', 'vehicle', 'vehicle_info', 'category', 'category_name',
            'rental', 'date', 'description', 'amount', 'receipt_number',
            'vendor', 'is_approved', 'approved_by', 'approved_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['approved_at', 'created_at', 'updated_at', 'created_by']
    
    def get_vehicle_info(self, obj):
        return {
            'id': obj.vehicle.id,
            'registration_number': obj.vehicle.registration_number,
            'brand': obj.vehicle.brand.name,
            'model': obj.vehicle.model,
        }


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    vehicle_info = serializers.SerializerMethodField()
    
    class Meta:
        model = MaintenanceRecord
        fields = [
            'id', 'vehicle', 'vehicle_info', 'maintenance_type', 'date_scheduled',
            'date_completed', 'mileage', 'service_description', 'parts_replaced',
            'service_provider', 'labor_cost', 'parts_cost', 'other_costs',
            'total_cost', 'invoice_number', 'warranty_until', 'status',
            'notes', 'next_service_mileage', 'next_service_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['total_cost', 'created_at', 'updated_at', 'created_by']
    
    def get_vehicle_info(self, obj):
        return {
            'id': obj.vehicle.id,
            'registration_number': obj.vehicle.registration_number,
            'brand': obj.vehicle.brand.name,
            'model': obj.vehicle.model,
        }
    
    def validate(self, data):
        if data.get('date_completed') and data['date_completed'] < data['date_scheduled']:
            raise serializers.ValidationError("Completion date cannot be before scheduled date.")
        
        return data


class RentalEvaluationSerializer(serializers.ModelSerializer):
    rental_info = serializers.SerializerMethodField()
    customer_info = serializers.SerializerMethodField()
    vehicle_info = serializers.SerializerMethodField()
    average_rating = serializers.ReadOnlyField()
    rating_stars = serializers.ReadOnlyField()
    
    class Meta:
        model = RentalEvaluation
        fields = [
            'id', 'rental', 'rental_info', 'customer_info', 'vehicle_info',
            'overall_rating', 'vehicle_condition_rating', 'service_quality_rating',
            'value_for_money_rating', 'average_rating', 'rating_stars',
            'comments', 'would_recommend', 'had_issues', 'issue_description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'average_rating', 'rating_stars']
    
    def get_rental_info(self, obj):
        return {
            'id': obj.rental.id,
            'start_date': obj.rental.start_date,
            'end_date': obj.rental.end_date,
            'actual_return_date': obj.rental.actual_return_date,
            'total_amount': obj.rental.total_amount,
            'status': obj.rental.status
        }
    
    def get_customer_info(self, obj):
        return {
            'id': obj.rental.customer.id,
            'full_name': obj.rental.customer.full_name,
            'email': obj.rental.customer.email
        }
    
    def get_vehicle_info(self, obj):
        return {
            'id': obj.rental.vehicle.id,
            'registration_number': obj.rental.vehicle.registration_number,
            'brand': obj.rental.vehicle.brand.name,
            'model': obj.rental.vehicle.model,
            'year': obj.rental.vehicle.year
        }
    
    def validate(self, data):
        # Ensure the rental is completed before allowing evaluation
        rental = data.get('rental')
        if rental and rental.status != 'completed':
            raise serializers.ValidationError("Only completed rentals can be evaluated.")
        
        # Validate rating ranges
        rating_fields = ['overall_rating', 'vehicle_condition_rating', 'service_quality_rating', 'value_for_money_rating']
        for field in rating_fields:
            rating = data.get(field)
            if rating and (rating < 1 or rating > 5):
                raise serializers.ValidationError(f"{field} must be between 1 and 5.")
        
        # If had_issues is True, issue_description should be provided
        if data.get('had_issues') and not data.get('issue_description'):
            raise serializers.ValidationError("Please provide issue description when indicating there were issues.")
        
        return data


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for customer self-registration"""
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number', 'birth_date',
            'address_line_1', 'address_line_2', 'city', 'postal_code', 'country',
            'id_number', 'driving_license_number', 'license_issue_date', 'license_expiry_date',
            'password', 'password_confirm'
        ]
        read_only_fields = ['id']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove the automatic unique validators for email and driving_license_number
        # so we can handle uniqueness validation ourselves
        print("=== Removing unique validators ===")
        
        # Remove unique validator from email field
        if 'email' in self.fields:
            email_field = self.fields['email']
            email_field.validators = [v for v in email_field.validators if not hasattr(v, 'queryset')]

        # Remove unique validator from driving_license_number field
        if 'driving_license_number' in self.fields:
            license_field = self.fields['driving_license_number']
            license_field.validators = [v for v in license_field.validators if not hasattr(v, 'queryset')]

    def validate_email(self, value):

        existing_customer = Customer.objects.filter(email=value).first()

        if existing_customer:

            # Only raise error if customer already has a user account
            if existing_customer.user is not None:
                #print("Email validation failed - customer has active account")
                raise serializers.ValidationError("Customer with this email already exists.")

        return value
    
    def validate_driving_license_number(self, value):
        existing_customer = Customer.objects.filter(driving_license_number=value).first()

        if existing_customer:
            # Only raise error if customer already has a user account
            if existing_customer.user is not None:
                #print("License validation failed - customer has active account")
                raise serializers.ValidationError("Customer with this driving license number already exists.")
        return value
    
    def validate(self, data):
        # Check password match
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        errors = {}
        
        # Check if customer exists with this email
        existing_customer_email = Customer.objects.filter(email=data.get('email')).first()
        if existing_customer_email:
            # If customer exists but has no user associated, we'll allow registration
            # to create the user and link it to the existing customer
            if existing_customer_email.user is not None:
                errors["email"] = "Customer with this email already exists."
        
        # Check if customer exists with this driving license number
        existing_customer_license = Customer.objects.filter(driving_license_number=data.get('driving_license_number')).first()
        if existing_customer_license:
            # If customer exists but has no user associated, we'll allow registration
            # to create the user and link it to the existing customer
            if existing_customer_license.user is not None:
                errors["driving_license_number"] = "Customer with this driving license number already exists."
            # Check if the existing customers with email and license are different records
            elif existing_customer_email and existing_customer_email.id != existing_customer_license.id:
                errors["driving_license_number"] = "This driving license number belongs to a different customer than the email provided."
        
        # Check if driving license is expired
        #from django.utils import timezone
        #if data.get('license_expiry_date') and data.get('license_expiry_date') < timezone.now().date():
        #    errors["license_expiry_date"] = "Driving license has expired."
        
        if errors:
            raise serializers.ValidationError(errors)

        return data
    
    def create(self, validated_data):
        from django.contrib.auth.models import User, Group
        
        # Remove password confirmation from data
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        
        # Check if customer already exists with this email or driving license
        existing_customer = Customer.objects.filter(
            email=validated_data['email']
        ).first()
        
        if not existing_customer:
            existing_customer = Customer.objects.filter(
                driving_license_number=validated_data['driving_license_number']
            ).first()
        
        if existing_customer and existing_customer.user is None:
            # Customer exists but has no user - create user and update customer
            user = User.objects.create_user(
                username=validated_data['email'],
                email=validated_data['email'],
                password=password,
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name']
            )
            
            # Add user to customer group
            customer_group, created = Group.objects.get_or_create(name='Customer')
            user.groups.add(customer_group)
            
            # Update existing customer with new data and link to user
            for key, value in validated_data.items():
                setattr(existing_customer, key, value)
            existing_customer.user = user
            existing_customer.save()
            
            return existing_customer
        else:
            # Create new customer and user
            user = User.objects.create_user(
                username=validated_data['email'],
                email=validated_data['email'],
                password=password,
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name']
            )
            
            # Add user to customer group
            customer_group, created = Group.objects.get_or_create(name='Customer')
            user.groups.add(customer_group)
            
            # Create customer profile
            customer = Customer.objects.create(user=user, **validated_data)
            
            return customer


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Serializer for customer detail view"""
    username = serializers.CharField(source='user.username', read_only=True)
    rental_count = serializers.SerializerMethodField()
    active_rentals = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 'phone_number', 'birth_date',
            'address_line_1', 'address_line_2', 'city', 'postal_code', 'country',
            'id_number', 'driving_license_number', 'license_issue_date', 'license_expiry_date',
            'is_blacklisted', 'rental_count', 'active_rentals', 'created_at'
        ]
        read_only_fields = ['id', 'username', 'is_blacklisted', 'created_at']
    
    def get_rental_count(self, obj):
        return obj.rentals.count()
    
    def get_active_rentals(self, obj):
        return obj.rentals.filter(status__in=['pending', 'confirmed', 'active']).count()


class CustomerRentalSerializer(serializers.ModelSerializer):
    """Serializer for customer viewing their own rentals"""
    vehicle_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    evaluation = serializers.SerializerMethodField()
    days_duration = serializers.SerializerMethodField()
    pickup_location_info = serializers.SerializerMethodField()
    return_location_info = serializers.SerializerMethodField()
    payment_details = serializers.SerializerMethodField()
    service_fees = serializers.SerializerMethodField()
    
    class Meta:
        model = Rental
        fields = [
            'id', 'vehicle_info', 'start_date', 'end_date', 'days_duration',
            'currency', 'daily_rate', 'subtotal', 'total_amount',
            'pickup_location_info', 'return_location_info',
            'driver', 'car_seat', 'payment_details', 'service_fees',
            'status', 'status_display', 'notes', 'evaluation', 'created_at'
        ]
        read_only_fields = ['id', 'total_amount', 'created_at']
    
    def get_vehicle_info(self, obj):
        return {
            'id': obj.vehicle.id,
            'brand': obj.vehicle.brand.name if obj.vehicle.brand else None,
            'model': obj.vehicle.model,
            'year': obj.vehicle.year,
            'registration_number': obj.vehicle.registration_number,
            'photo': obj.vehicle.photo.url if obj.vehicle.photo else None,
            'primary_photo': self.get_primary_photo(obj.vehicle)['image'] if self.get_primary_photo(obj.vehicle) else None
        }
    
    def get_evaluation(self, obj):
        try:
            # Use 'evaluation' (singular) as per the model's related_name
            if hasattr(obj, 'evaluation'):
                evaluation = obj.evaluation
                return {
                    'id': evaluation.id,
                    'overall_rating': evaluation.overall_rating,
                    'comments': evaluation.comments,
                    'created_at': evaluation.created_at
                }
        except RentalEvaluation.DoesNotExist:
            pass
        except Exception:
            pass
        return None

    def get_days_duration(self, obj):
        if obj.start_date and obj.end_date:
            return (obj.end_date - obj.start_date).days
        return None
    
    def get_pickup_location_info(self, obj):
        """Get pickup location details"""
        if obj.pickup_location:
            return DeliveryLocationSerializer(obj.pickup_location).data
        return None
    
    def get_return_location_info(self, obj):
        """Get return location details"""
        if obj.return_location:
            return DeliveryLocationSerializer(obj.return_location).data
        return None
    
    def get_payment_details(self, obj):
        """Get detailed payment breakdown"""
        return {
            'driver_requested': obj.driver,
            'driver_fee_per_day': float(obj.driver_fee / obj.number_of_days) if obj.driver and obj.number_of_days > 0 else 0,
            'driver_fee_total': float(obj.driver_fee),
            'car_seat_requested': obj.car_seat,
            'car_seat_fee_per_day': float(obj.car_seat_fee / obj.number_of_days) if obj.car_seat and obj.number_of_days > 0 else 0,
            'car_seat_fee_total': float(obj.car_seat_fee),
            'subtotal': float(obj.subtotal),
            'total_services_fees': float(obj.driver_fee + obj.car_seat_fee),
            'total_amount': float(obj.total_amount)
        }
    
    def get_service_fees(self, obj):
        """Get all service fees and charges"""
        return {
            'insurance_fee': float(obj.insurance_fee) if obj.insurance_fee else 0,
            'security_deposit': float(obj.security_deposit) if obj.security_deposit else 0,
            'commission_percent': float(obj.commission_percent) if obj.commission_percent else 0,
            'commission_amount': float(obj.commission_amount) if obj.commission_amount else 0,
            'late_return_fee': float(obj.late_return_fee) if obj.late_return_fee else 0,
            'damage_fee': float(obj.damage_fee) if obj.damage_fee else 0
        }

    def get_primary_photo(self, obj):
        """Get the primary photo if exists"""
        primary_photo = obj.additional_photos.filter(is_primary=True).first()
        if primary_photo:
            return VehiclePhotoSerializer(primary_photo, context=self.context).data
        return None


class CustomerVehicleSerializer(serializers.ModelSerializer):
    """Simplified vehicle serializer for customer-facing API to avoid performance issues"""
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    photos_count = serializers.SerializerMethodField()
    active_rentals = serializers.SerializerMethodField()
    basic_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'brand', 'brand_name', 'model', 'year', 'description', 'description_en', 'description_fr',
            'registration_number', 'color', 'photo', 'fuel_type',
            'gearbox_type', 'panoramic_roof', 'air_conditioning', 'number_of_seats',
            'daily_rate', 'status', 'is_available', 'photos_count', 'active_rentals',
            'basic_stats'
        ]
    
    def get_photos_count(self, obj):
        """Get total number of additional photos"""
        try:
            return obj.additional_photos.count()
        except:
            return 0
    
    def get_active_rentals(self, obj):
        """Get list of rentals where end_date >= today"""
        from django.utils import timezone
        today = timezone.now().date()
        
        active_rentals = obj.rentals.filter(
            end_date__date__gte=today
        ).select_related('customer').order_by('start_date')
        
        return [
            {
                'id': rental.id,
                'customer': rental.customer.full_name,
                'start_date': rental.start_date,
                'end_date': rental.end_date,
                'status': rental.status,
                'status_display': rental.get_status_display(),
            }
            for rental in active_rentals
        ]
    
    def get_basic_stats(self, obj):
        """Get basic statistics for customer view (performance optimized)"""
        from django.db.models import Avg, Count
        
        # Use efficient queries to get basic stats
        evaluations = obj.rentals.filter(evaluation__isnull=False).select_related('evaluation')
        
        basic_stats = {
            'total_rentals': obj.rentals.count(),
            'total_evaluations': evaluations.count(),
            'average_rating': 0,
            'recommendation_percentage': 0
        }
        
        if evaluations.exists():
            evaluations_list = [rental.evaluation for rental in evaluations]
            total_evals = len(evaluations_list)
            
            # Calculate average rating
            avg_rating = sum(e.overall_rating for e in evaluations_list) / total_evals
            basic_stats['average_rating'] = round(avg_rating, 1)
            
            # Calculate recommendation percentage
            recommendations = sum(1 for e in evaluations_list if e.would_recommend)
            basic_stats['recommendation_percentage'] = round(
                (recommendations / total_evals) * 100, 0
            )
        
        return basic_stats


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing customer password"""
    customer_id = serializers.IntegerField()
    current_password = serializers.CharField(min_length=1, style={'input_type': 'password'})
    new_password = serializers.CharField(min_length=8, style={'input_type': 'password'})
    confirm_password = serializers.CharField(min_length=1, style={'input_type': 'password'})
    
    def validate(self, data):
        """Validate the password change data"""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "New password and confirmation do not match"
            })
        
        # Check if customer exists
        try:
            customer = Customer.objects.get(id=data['customer_id'])
        except Customer.DoesNotExist:
            raise serializers.ValidationError({
                "customer_id": "Customer not found"
            })
        
        # Check if customer has a user account
        if not customer.user:
            raise serializers.ValidationError({
                "customer_id": "Customer does not have a user account"
            })
        
        # Verify current password
        if not customer.user.check_password(data['current_password']):
            raise serializers.ValidationError({
                "current_password": "Current password is incorrect"
            })
        
        # Store customer in validated_data for use in the view
        data['customer'] = customer
        return data


class CustomerNotificationSerializer(serializers.ModelSerializer):
    """Serializer for customer notifications"""
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    rental_id = serializers.IntegerField(source='rental.id', read_only=True, allow_null=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CustomerNotification
        fields = [
            'id', 'customer', 'customer_name', 'customer_email',
            'rental', 'rental_id', 'notification_type', 'notification_type_display',
            'recipient_email', 'subject', 'content', 'html_content',
            'status', 'status_display', 'error_message', 'attempt_count',
            'created_at', 'sent_at', 'created_by'
        ]
        read_only_fields = [
            'id', 'customer_name', 'customer_email', 'rental_id',
            'notification_type_display', 'status_display', 'created_at',
            'sent_at', 'created_by'
        ]



class SystemConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for system configuration/rates"""
    
    # Read-only fields for converted rates
    driver_rate_eur = serializers.ReadOnlyField()
    driver_rate_usd = serializers.ReadOnlyField()
    car_seat_rate_eur = serializers.ReadOnlyField()
    car_seat_rate_usd = serializers.ReadOnlyField()

    # Service fee info
    service_fee_type = serializers.ReadOnlyField()
    service_fee_usd = serializers.SerializerMethodField()
    service_fee_eur = serializers.SerializerMethodField()
    
    class Meta:
        model = SystemConfiguration
        fields = [
            'id',
            'service_fee_percentage',
            'service_fee_amount',
            'service_fee_type',
            'driver_daily_rate',
            'car_seat_daily_rate',
            'euro_exchange_rate',
            'usd_exchange_rate',
            'driver_rate_eur',
            'driver_rate_usd',
            'car_seat_rate_eur',
            'car_seat_rate_usd',
            'service_fee_eur',
            'service_fee_usd',
            'last_updated'
        ]
        read_only_fields = ['last_updated', 'service_fee_type']

    def get_service_fee_eur(self, obj):
        """Get service fee in EUR (only for fixed amounts)"""
        if obj.service_fee_amount is not None:
            return round(obj.service_fee_amount / obj.euro_exchange_rate, 2)
        return None  # Percentage fees don't have currency conversion
    
    def get_service_fee_usd(self, obj):
        """Get service fee in USD (only for fixed amounts)"""
        if obj.service_fee_amount is not None:
            return round(obj.service_fee_amount / obj.usd_exchange_rate, 2)
        return None  # Percentage fees don't have currency conversion
