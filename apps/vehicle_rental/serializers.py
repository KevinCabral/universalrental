from rest_framework import serializers
from .models import Vehicle, VehicleBrand, Customer, Rental, Expense, ExpenseCategory, MaintenanceRecord, RentalEvaluation, VehiclePhoto


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
    additional_photos = VehiclePhotoSerializer(many=True, read_only=True)
    photos_count = serializers.SerializerMethodField()
    primary_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'brand', 'brand_name', 'model', 'year', 'description', 'chassis_number',
            'registration_number', 'color', 'photo', 'engine_size', 'fuel_type',
            'gearbox_type', 'panoramic_roof', 'air_conditioning', 'number_of_seats',
            'mileage', 'purchase_price', 'date_of_purchase', 'daily_rate',
            'status', 'is_active', 'is_available', 'current_rental',
            'additional_photos', 'photos_count', 'primary_photo',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'additional_photos', 'photos_count', 'primary_photo']
    
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
    
    def get_photos_count(self, obj):
        """Get total number of additional photos"""
        return obj.additional_photos.count()
    
    def get_primary_photo(self, obj):
        """Get the primary photo if exists"""
        primary_photo = obj.additional_photos.filter(is_primary=True).first()
        if primary_photo:
            return VehiclePhotoSerializer(primary_photo, context=self.context).data
        return None


class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    can_rent = serializers.BooleanField(read_only=True)
    rental_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email',
            'phone_number', 'address_line_1', 'address_line_2', 'city',
            'postal_code', 'country', 'id_number', 'driving_license_number',
            'license_expiry_date', 'is_blacklisted', 'blacklist_reason',
            'can_rent', 'rental_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_rental_count(self, obj):
        return obj.rentals.count()
    
    def validate_email(self, value):
        if Customer.objects.filter(email=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("A customer with this email already exists.")
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
            'start_date', 'end_date', 'actual_return_date', 'daily_rate',
            'number_of_days', 'subtotal', 'commission_percent', 'commission_amount',
            'insurance_fee', 'security_deposit', 'late_return_fee', 'damage_fee',
            'total_amount', 'amount_paid', 'mileage_start', 'mileage_end',
            'fuel_level_start', 'fuel_level_end', 'status', 'notes',
            'is_overdue', 'days_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'number_of_days', 'subtotal', 'commission_amount', 'total_amount',
            'created_at', 'updated_at', 'created_by'
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
            status__in=['confirmed', 'active'],
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
            'id', 'first_name', 'last_name', 'email', 'phone_number',
            'address_line_1', 'address_line_2', 'city', 'postal_code', 'country',
            'id_number', 'driving_license_number', 'license_expiry_date',
            'password', 'password_confirm'
        ]
        read_only_fields = ['id']
    
    def validate(self, data):
        # Check password match
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        # Check if email already exists
        if Customer.objects.filter(email=data.get('email')).exists():
            raise serializers.ValidationError({"email": "A customer with this email already exists."})
        
        # Check if driving license is expired
        from django.utils import timezone
        if data.get('license_expiry_date') and data.get('license_expiry_date') < timezone.now().date():
            raise serializers.ValidationError({"license_expiry_date": "Driving license has expired."})
        
        return data
    
    def create(self, validated_data):
        from django.contrib.auth.models import User, Group
        
        # Remove password confirmation from data
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        
        # Create Django user
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=password,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        
        # Add user to customer group
        customer_group, created = Group.objects.get_or_create(name='customer')
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
            'id', 'username', 'first_name', 'last_name', 'email', 'phone_number',
            'address_line_1', 'address_line_2', 'city', 'postal_code', 'country',
            'id_number', 'driving_license_number', 'license_expiry_date',
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
    
    class Meta:
        model = Rental
        fields = [
            'id', 'vehicle_info', 'start_date', 'end_date', 'days_duration',
            'total_amount', 'status', 'status_display', 'notes',
            'evaluation', 'created_at'
        ]
        read_only_fields = ['id', 'total_amount', 'created_at']
    
    def get_vehicle_info(self, obj):
        return {
            'id': obj.vehicle.id,
            'brand': obj.vehicle.brand.name if obj.vehicle.brand else None,
            'model': obj.vehicle.model,
            'year': obj.vehicle.year,
            'registration_number': obj.vehicle.registration_number,
            'photo': obj.vehicle.photo.url if obj.vehicle.photo else None
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


class CustomerVehicleSerializer(serializers.ModelSerializer):
    """Simplified vehicle serializer for customer-facing API to avoid performance issues"""
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    photos_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'brand', 'brand_name', 'model', 'year', 'description',
            'registration_number', 'color', 'photo', 'fuel_type',
            'gearbox_type', 'panoramic_roof', 'air_conditioning', 'number_of_seats',
            'daily_rate', 'status', 'is_available', 'photos_count'
        ]
    
    def get_photos_count(self, obj):
        """Get total number of additional photos"""
        try:
            return obj.additional_photos.count()
        except:
            return 0
