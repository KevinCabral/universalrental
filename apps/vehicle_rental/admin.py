from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    VehicleBrand, Vehicle, Customer, Rental, 
    ExpenseCategory, Expense, MaintenanceRecord, RentalPhoto, RentalEvaluation
)


@admin.register(VehicleBrand)
class VehicleBrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'country_of_origin', 'vehicle_count', 'created_at']
    search_fields = ['name', 'country_of_origin']
    list_filter = ['country_of_origin', 'created_at']
    
    def vehicle_count(self, obj):
        return obj.vehicles.count()
    vehicle_count.short_description = 'Vehicles'


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        'registration_number', 'brand', 'model', 'year', 
        'status', 'daily_rate', 'mileage', 'is_active'
    ]
    list_filter = [
        'status', 'brand', 'fuel_type', 'gearbox_type', 
        'is_active', 'year'
    ]
    search_fields = [
        'registration_number', 'chassis_number', 'brand__name', 
        'model', 'color'
    ]
    list_editable = ['status', 'daily_rate', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('brand', 'model', 'year', 'color')
        }),
        ('Identification', {
            'fields': ('chassis_number', 'registration_number')
        }),
        ('Technical Specifications', {
            'fields': ('engine_size', 'fuel_type', 'gearbox_type', 'number_of_seats')
        }),
        ('Features', {
            'fields': ('panoramic_roof', 'air_conditioning')
        }),
        ('Operational Data', {
            'fields': ('mileage', 'purchase_price', 'date_of_purchase', 'daily_rate')
        }),
        ('Status', {
            'fields': ('status', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('brand')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'email', 'phone_number', 'id_number',
        'license_expiry_date', 'rental_count', 'is_blacklisted'
    ]
    list_filter = ['is_blacklisted', 'country', 'license_expiry_date']
    search_fields = [
        'first_name', 'last_name', 'email', 'phone_number', 
        'id_number', 'driving_license_number'
    ]
    list_editable = ['is_blacklisted']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number')
        }),
        ('Address', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'postal_code', 'country')
        }),
        ('Identification', {
            'fields': ('id_number', 'driving_license_number', 'license_expiry_date')
        }),
        ('Status', {
            'fields': ('is_blacklisted', 'blacklist_reason')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def rental_count(self, obj):
        return obj.rentals.count()
    rental_count.short_description = 'Rentals'


# Inline admin for photos in rental detail
class RentalPhotoInline(admin.TabularInline):
    model = RentalPhoto
    extra = 0
    readonly_fields = ['image_preview', 'taken_at', 'taken_by']
    fields = ['photo_type', 'image', 'image_preview', 'description', 'taken_at', 'taken_by']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 75px; border-radius: 3px;" />',
                obj.image.url
            )
        return "Sem imagem"
    image_preview.short_description = 'Preview'


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'customer', 'vehicle', 'start_date', 'end_date',
        'status', 'total_amount', 'days_remaining'
    ]
    list_filter = [
        'status', 'start_date', 'end_date', 'vehicle__brand'
    ]
    search_fields = [
        'customer__first_name', 'customer__last_name',
        'vehicle__registration_number', 'vehicle__brand__name'
    ]
    list_editable = ['status']
    readonly_fields = [
        'number_of_days', 'subtotal', 'commission_amount', 
        'total_amount', 'created_at', 'updated_at'
    ]
    inlines = [RentalPhotoInline]
    
    fieldsets = (
        ('Rental Information', {
            'fields': ('customer', 'vehicle', 'start_date', 'end_date', 'actual_return_date')
        }),
        ('Pricing', {
            'fields': (
                'daily_rate', 'number_of_days', 'subtotal',
                'commission_percent', 'commission_amount'
            )
        }),
        ('Additional Charges', {
            'fields': ('insurance_fee', 'security_deposit', 'late_return_fee', 'damage_fee')
        }),
        ('Payment', {
            'fields': ('total_amount', 'amount_paid')
        }),
        ('Vehicle Condition', {
            'fields': (
                'mileage_start', 'mileage_end',
                'fuel_level_start', 'fuel_level_end'
            )
        }),
        ('Status & Notes', {
            'fields': ('status', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def days_remaining(self, obj):
        if obj.status == 'active' and obj.end_date:
            from django.utils import timezone
            remaining = (obj.end_date - timezone.now()).days
            if remaining < 0:
                return format_html('<span style="color: red;">Overdue by {} days</span>', abs(remaining))
            elif remaining == 0:
                return format_html('<span style="color: orange;">Due today</span>')
            else:
                return f"{remaining} days"
        return "-"
    days_remaining.short_description = 'Days Remaining'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer', 'vehicle', 'vehicle__brand')


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'expense_count', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    
    def expense_count(self, obj):
        return obj.expenses.count()
    expense_count.short_description = 'Expenses'


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'vehicle', 'category', 'description_short',
        'amount', 'vendor', 'is_approved'
    ]
    list_filter = [
        'category', 'date', 'is_approved', 'vehicle__brand'
    ]
    search_fields = [
        'description', 'vendor', 'receipt_number',
        'vehicle__registration_number'
    ]
    list_editable = ['is_approved']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    
    fieldsets = (
        ('Expense Details', {
            'fields': ('vehicle', 'category', 'rental', 'date', 'description', 'amount')
        }),
        ('Documentation', {
            'fields': ('receipt_number', 'vendor')
        }),
        ('Approval', {
            'fields': ('is_approved', 'approved_by', 'approved_at')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def description_short(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vehicle', 'category', 'rental')


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = [
        'vehicle', 'maintenance_type', 'date_scheduled',
        'date_completed', 'status', 'total_cost', 'service_provider'
    ]
    list_filter = [
        'maintenance_type', 'status', 'date_scheduled',
        'vehicle__brand'
    ]
    search_fields = [
        'vehicle__registration_number', 'service_description',
        'service_provider', 'invoice_number'
    ]
    list_editable = ['status']
    readonly_fields = ['total_cost', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Maintenance Information', {
            'fields': ('vehicle', 'maintenance_type', 'date_scheduled', 'date_completed')
        }),
        ('Service Details', {
            'fields': ('mileage', 'service_description', 'parts_replaced', 'service_provider')
        }),
        ('Cost Breakdown', {
            'fields': ('labor_cost', 'parts_cost', 'other_costs', 'total_cost')
        }),
        ('Documentation', {
            'fields': ('invoice_number', 'warranty_until')
        }),
        ('Next Service', {
            'fields': ('next_service_mileage', 'next_service_date')
        }),
        ('Status & Notes', {
            'fields': ('status', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vehicle', 'vehicle__brand')


@admin.register(RentalPhoto)
class RentalPhotoAdmin(admin.ModelAdmin):
    list_display = [
        'rental', 'get_photo_type_display', 'image_preview', 
        'taken_at', 'taken_by', 'is_start_photo'
    ]
    list_filter = [
        'photo_type', 'taken_at', 'taken_by'
    ]
    search_fields = [
        'rental__id', 'rental__customer__first_name', 
        'rental__customer__last_name', 'rental__vehicle__registration_number'
    ]
    readonly_fields = ['image_preview', 'taken_at', 'taken_by']
    
    fieldsets = (
        ('Photo Information', {
            'fields': ('rental', 'photo_type', 'image', 'image_preview', 'description')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('taken_at', 'taken_by'),
            'classes': ('collapse',)
        })
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 150px; border-radius: 5px;" />',
                obj.image.url
            )
        return "Sem imagem"
    image_preview.short_description = 'Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'rental', 'rental__customer', 'rental__vehicle', 'taken_by'
        )


@admin.register(RentalEvaluation)
class RentalEvaluationAdmin(admin.ModelAdmin):
    list_display = [
        'rental', 'customer_name', 'vehicle_info', 'overall_rating', 
        'average_rating', 'would_recommend', 'had_issues', 'created_at'
    ]
    list_filter = [
        'overall_rating', 'vehicle_condition_rating', 'service_quality_rating',
        'value_for_money_rating', 'would_recommend', 'had_issues', 'created_at'
    ]
    search_fields = [
        'rental__customer__first_name', 'rental__customer__last_name',
        'rental__vehicle__registration_number', 'rental__vehicle__brand__name',
        'rental__vehicle__model', 'comments', 'issue_description'
    ]
    readonly_fields = ['rental', 'average_rating', 'rating_stars', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Rental Information', {
            'fields': ('rental',)
        }),
        ('Ratings', {
            'fields': (
                'overall_rating', 'vehicle_condition_rating', 
                'service_quality_rating', 'value_for_money_rating',
                'average_rating', 'rating_stars'
            )
        }),
        ('Feedback', {
            'fields': ('comments', 'would_recommend')
        }),
        ('Issues', {
            'fields': ('had_issues', 'issue_description'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_name(self, obj):
        return obj.rental.customer.full_name
    customer_name.short_description = 'Customer'
    customer_name.admin_order_field = 'rental__customer__first_name'
    
    def vehicle_info(self, obj):
        return f"{obj.rental.vehicle.brand.name} {obj.rental.vehicle.model} ({obj.rental.vehicle.registration_number})"
    vehicle_info.short_description = 'Vehicle'
    vehicle_info.admin_order_field = 'rental__vehicle__registration_number'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'rental__customer', 'rental__vehicle__brand'
        )


# Custom admin site configuration
admin.site.site_header = "Vehicle Rental Management"
admin.site.site_title = "Vehicle Rental Admin"
admin.site.index_title = "Welcome to Vehicle Rental Management System"
