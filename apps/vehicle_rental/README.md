# Vehicle Rental Management System

A comprehensive Django application for managing vehicle rental business operations.

## Features

### Core Models
- **Vehicle Management**: Complete vehicle information with brands, specifications, and status tracking
- **Customer Management**: Customer profiles with verification and blacklisting capabilities
- **Rental Management**: Full rental lifecycle from booking to completion
- **Expense Tracking**: Categorized expense management with approval workflow
- **Maintenance Records**: Scheduled and completed maintenance tracking

### Key Improvements Made

1. **Enhanced Data Models**:
   - Added proper relationships between models
   - Implemented validation and constraints
   - Added lookup tables for brands and expense categories
   - Included comprehensive metadata fields

2. **Better Field Types**:
   - Used DecimalField for monetary values
   - Added choices for categorical fields
   - Implemented proper validation
   - Added indexes for performance

3. **Business Logic**:
   - Vehicle availability checking
   - Automatic pricing calculations
   - Status management through signals
   - Rental overlap prevention

4. **Admin Interface**:
   - Custom admin classes with filtering and search
   - Inline editing capabilities
   - Custom display methods
   - Bulk operations support

5. **API Integration**:
   - Django REST Framework integration
   - Comprehensive serializers
   - Custom endpoints for business logic
   - Authentication support

## Model Relationships

```
VehicleBrand (1) ←→ (N) Vehicle
Vehicle (1) ←→ (N) Rental
Vehicle (1) ←→ (N) Expense
Vehicle (1) ←→ (N) MaintenanceRecord
Customer (1) ←→ (N) Rental
Rental (1) ←→ (N) Expense
ExpenseCategory (1) ←→ (N) Expense
```

## Installation & Setup

1. **Add to INSTALLED_APPS**:
```python
INSTALLED_APPS = [
    # ... other apps
    'apps.vehicle_rental',
    # ... rest framework
    'rest_framework',
    'rest_framework.authtoken',
]
```

2. **Run Migrations**:
```bash
python manage.py makemigrations vehicle_rental
python manage.py migrate
```

3. **Load Sample Data**:
```bash
python manage.py load_sample_data
```

4. **Create Superuser**:
```bash
python manage.py createsuperuser
```

## Usage

### Admin Interface
Access the admin interface at `/admin/` to manage:
- Vehicle brands and vehicles
- Customers and rentals
- Expenses and maintenance records

### API Endpoints
- `/vehicle-rental/api/vehicles/` - Vehicle CRUD operations
- `/vehicle-rental/api/customers/` - Customer management
- `/vehicle-rental/api/rentals/` - Rental management
- `/vehicle-rental/api/expenses/` - Expense tracking
- `/vehicle-rental/api/maintenance/` - Maintenance records

### Web Interface
- `/vehicle-rental/` - Dashboard
- `/vehicle-rental/vehicles/` - Vehicle list
- `/vehicle-rental/customers/` - Customer list
- `/vehicle-rental/rentals/` - Rental management
- `/vehicle-rental/reports/` - Reports and analytics

## Key Features

### Vehicle Management
- Complete vehicle specifications
- Status tracking (available, rented, maintenance, retired)
- Mileage and maintenance tracking
- Daily rate management

### Customer Management
- Personal and contact information
- ID and driving license verification
- Blacklisting capability
- Rental history tracking

### Rental Management
- Date and pricing management
- Vehicle availability checking
- Commission calculation
- Late return and damage fees
- Fuel level tracking

### Expense Management
- Categorized expenses
- Vehicle-specific and rental-specific expenses
- Approval workflow
- Receipt and vendor tracking

### Maintenance Management
- Scheduled and completed maintenance
- Cost breakdown (labor, parts, other)
- Warranty tracking
- Next service scheduling

## Business Rules

1. **Vehicle Availability**: Vehicles cannot be double-booked
2. **Customer Verification**: Blacklisted customers cannot rent
3. **License Validation**: Expired licenses prevent rentals
4. **Status Management**: Vehicle status updates automatically based on rentals/maintenance
5. **Pricing Calculation**: Automatic calculation of totals including commission and fees

## Signals

The app includes Django signals for:
- Automatic rental calculations
- Vehicle status updates
- Maintenance cost calculations
- Mileage updates

## Sample Data

The app includes management commands and fixtures for:
- Vehicle brands (Toyota, Ford, Nissan, etc.)
- Expense categories (Fuel, Maintenance, Repairs, etc.)
- Sample vehicles and customers

## API Authentication

The app supports both session and token authentication for API access.

## Future Enhancements

- Payment processing integration
- SMS/Email notifications
- Advanced reporting and analytics
- Mobile app support
- Insurance integration
- GPS tracking integration
