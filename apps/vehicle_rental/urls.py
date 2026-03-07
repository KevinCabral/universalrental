from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'vehicle_rental'

# DRF Router for API endpoints (Admin/Backoffice)
router = DefaultRouter()
router.register(r'vehicles', views.VehicleViewSet)
router.register(r'customers', views.CustomerViewSet)
router.register(r'vehicle-brands', views.VehicleBrandViewSet)
router.register(r'delivery-locations', views.DeliveryLocationViewSet)
router.register(r'rentals', views.RentalViewSet)
router.register(r'expenses', views.ExpenseViewSet)
router.register(r'maintenance', views.MaintenanceRecordViewSet)
router.register(r'evaluations', views.RentalEvaluationViewSet)
router.register(r'vehicle-photos', views.VehiclePhotoViewSet)
router.register(r'system-config', views.SystemConfigurationViewSet, basename='system-config')

# Customer-facing API Router
customer_router = DefaultRouter()
customer_router.register(r'register', views.CustomerRegistrationViewSet, basename='customer-register')
customer_router.register(r'rentals', views.CustomerRentalViewSet, basename='customer-rentals')
customer_router.register(r'evaluations', views.CustomerRentalEvaluationViewSet, basename='customer-evaluations')
customer_router.register(r'vehicles', views.VehicleAvailabilityViewSet, basename='customer-vehicles')
customer_router.register(r'vehicle-brands', views.VehicleBrandViewSet, basename='customer-vehicle-brands')
customer_router.register(r'delivery-locations', views.DeliveryLocationViewSet, basename='customer-delivery-locations')

urlpatterns = [
    # Dashboard and main views
    path('', views.dashboard, name='dashboard'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/calendar/', views.rental_calendar, name='rental_calendar'),
    path('vehicles/create/', views.vehicle_create, name='vehicle_create'),
    path('vehicles/<int:pk>/', views.vehicle_detail, name='vehicle_detail'),
    path('vehicles/<int:pk>/edit/', views.vehicle_edit, name='vehicle_edit'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('rentals/', views.rental_list, name='rental_list'),
    path('rentals/<int:pk>/', views.rental_detail, name='rental_detail'),
    path('rentals/create/', views.rental_create, name='rental_create'),
    path('rentals/<int:pk>/edit/', views.rental_edit, name='rental_edit'),
    path('rentals/<int:pk>/confirm/', views.rental_confirm, name='rental_confirm'),
    path('rentals/<int:pk>/cancel/', views.rental_cancel, name='rental_cancel'),
    path('rentals/<int:pk>/return/', views.rental_return, name='rental_return'),
    path('rentals/<int:pk>/photos/', views.rental_photos, name='rental_photos'),
    path('rentals/<int:pk>/invoice/', views.rental_invoice, name='rental_invoice'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/export/', views.expense_export_invoice, name='expense_export_invoice'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    path('maintenance/create/', views.maintenance_create, name='maintenance_create'),
    path('maintenance/<int:pk>/', views.maintenance_detail, name='maintenance_detail'),
    path('maintenance/<int:pk>/edit/', views.maintenance_edit, name='maintenance_edit'),
    
    # Parameterization – Brands
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/create/', views.brand_create, name='brand_create'),
    path('brands/<int:pk>/edit/', views.brand_edit, name='brand_edit'),
    path('brands/<int:pk>/delete/', views.brand_delete, name='brand_delete'),

    # Parameterization – Delivery Locations
    path('locations/', views.location_list, name='location_list'),
    path('locations/create/', views.location_create, name='location_create'),
    path('locations/<int:pk>/edit/', views.location_edit, name='location_edit'),
    path('locations/<int:pk>/delete/', views.location_delete, name='location_delete'),

    # Parameterization – Expense Categories
    path('expense-categories/', views.expense_category_list, name='expense_category_list'),
    path('expense-categories/create/', views.expense_category_create, name='expense_category_create'),
    path('expense-categories/<int:pk>/edit/', views.expense_category_edit, name='expense_category_edit'),
    path('expense-categories/<int:pk>/delete/', views.expense_category_delete, name='expense_category_delete'),

    # Parameterization – System Configuration
    path('system-config/', views.system_config_edit, name='system_config'),

    # Reports
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/revenue/', views.revenue_report, name='revenue_report'),
    path('reports/vehicle-utilization/', views.vehicle_utilization_report, name='vehicle_utilization_report'),
    
    # API endpoints (Admin/Backoffice)
    path('api/', include(router.urls)),
    
    # Customer-facing API endpoints
    path('api/customer/login/', views.customer_login, name='customer_login'),
    path('api/customer/change-password/', views.change_password, name='customer_change_password'),
    path('api/customer/request-password-reset/', views.request_password_reset, name='request_password_reset'),
    path('api/customer/reset-password/', views.reset_password, name='reset_password'),
    path('api/customer/', include(customer_router.urls)),
    
    # Public API endpoints (no authentication required)
    path('api/public/system-config/', views.SystemConfigurationAPIView.as_view(), name='system_configuration_api'),
    
    # AJAX endpoints
    path('ajax/vehicle-availability/', views.check_vehicle_availability, name='check_vehicle_availability'),
    path('ajax/rental-pricing/', views.calculate_rental_pricing, name='calculate_rental_pricing'),
    path('api/create-brand/', views.api_create_brand, name='api_create_brand'),
]
