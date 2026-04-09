import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from .models import (
    Vehicle, Customer, Rental, Expense, MaintenanceRecord, VehicleBrand,
    ExpenseCategory, RentalPhoto, RentalEvaluation, VehiclePhoto, DeliveryLocation,
    SystemConfiguration, CustomerNotification
)
from .forms import VehicleForm, CustomerForm, RentalForm
from .serializers import (
    VehicleSerializer, CustomerSerializer, RentalSerializer,
    ExpenseSerializer, MaintenanceRecordSerializer, RentalEvaluationSerializer, VehiclePhotoSerializer,
    VehicleBrandSerializer, ChangePasswordSerializer, DeliveryLocationSerializer, SystemConfigurationSerializer
)
from .forms import VehicleForm, CustomerForm, RentalForm, ExpenseForm, MaintenanceRecordForm, RentalStartPhotosFormSet, RentalReturnPhotosFormSet
from .forms import VehicleBrandForm, DeliveryLocationForm, ExpenseCategoryForm, SystemConfigurationForm
from .forms import UserCreateForm, UserEditForm, UserPasswordChangeForm, UserPermissionsForm
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
import calendar
import logging

logger = logging.getLogger(__name__)


# Helper function to display form errors as toast messages
def add_form_errors_to_messages(request, form):
    """Convert form validation errors to Django messages for toast display"""
    # Add non-field errors (general form errors)
    for error in form.non_field_errors():
        messages.error(request, error)
    
    # Add field-specific errors
    for field_name, errors in form.errors.items():
        if field_name != '__all__':  # Skip non-field errors (already handled)
            # Get the field label in Portuguese if available, otherwise use field name
            field_label = form.fields[field_name].label if field_name in form.fields else field_name
            for error in errors:
                messages.error(request, f"{field_label}: {error}")


# Dashboard and Main Views
@login_required
def dashboard(request):
    """Main dashboard with key metrics and recent activities"""
    
    # Key metrics
    total_vehicles = Vehicle.objects.filter(is_active=True).count()
    available_vehicles = Vehicle.objects.filter(status='available', is_active=True).count()
    active_rentals = Rental.objects.filter(status='active').count()
    overdue_rentals = Rental.objects.filter(
        status='active',
        end_date__lt=timezone.now()
    ).count()
    
    # Recent activities
    recent_rentals = Rental.objects.select_related('customer', 'vehicle').order_by('-created_at')[:5]
    upcoming_maintenance = MaintenanceRecord.objects.filter(
        status='scheduled',
        date_scheduled__lte=timezone.now() + timedelta(days=7)
    ).select_related('vehicle').order_by('date_scheduled')[:5]
    
    # Revenue this month
    current_month = timezone.now().replace(day=1)
    next_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    monthly_revenue = Rental.objects.filter(
        start_date__gte=current_month,
        start_date__lt=next_month,
        status__in=['confirmed', 'active', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Monthly expenses
    monthly_expenses = Expense.objects.filter(
        date__gte=current_month,
        date__lt=next_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Monthly maintenance costs
    monthly_maintenance_costs = MaintenanceRecord.objects.filter(
        date_scheduled__gte=current_month,
        date_scheduled__lt=next_month
    ).aggregate(total=Sum('total_cost'))['total'] or 0
    
    # Net profit (revenue - expenses - maintenance)
    monthly_profit = monthly_revenue - monthly_expenses - monthly_maintenance_costs
    
    context = {
        'total_vehicles': total_vehicles,
        'available_vehicles': available_vehicles,
        'active_rentals': active_rentals,
        'overdue_rentals': overdue_rentals,
        'recent_rentals': recent_rentals,
        'upcoming_maintenance': upcoming_maintenance,
        'monthly_revenue': monthly_revenue,
        'monthly_expenses': monthly_expenses,
        'monthly_maintenance_costs': monthly_maintenance_costs,
        'monthly_profit': monthly_profit,
    }
    
    return render(request, 'vehicle_rental/dashboard.html', context)


@login_required
def vehicle_list(request):
    """List all vehicles with filtering and pagination"""
    
    vehicles = Vehicle.objects.select_related('brand').filter(is_active=True)
    
    # Summary statistics for cards (before filtering)
    all_vehicles = Vehicle.objects.filter(is_active=True)
    total_vehicles = all_vehicles.count()
    available_vehicles = all_vehicles.filter(status='available').count()
    rented_vehicles = all_vehicles.filter(status='rented').count()
    maintenance_vehicles = all_vehicles.filter(status='maintenance').count()
    
    # Filtering
    brand_filter = request.GET.get('brand')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    
    if brand_filter and brand_filter.strip() and brand_filter != 'None':
        vehicles = vehicles.filter(brand_id=brand_filter)
    
    if status_filter and status_filter.strip() and status_filter != 'None':
        vehicles = vehicles.filter(status=status_filter)
    
    if search_query and search_query.strip() and search_query != 'None':
        vehicles = vehicles.filter(
            Q(registration_number__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(vehicles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Filter options
    brands = VehicleBrand.objects.all()
    status_choices = Vehicle.STATUS_CHOICES
    
    context = {
        'page_obj': page_obj,
        'brands': brands,
        'status_choices': status_choices,
        'current_brand': brand_filter if brand_filter and brand_filter != 'None' else '',
        'current_status': status_filter if status_filter and status_filter != 'None' else '',
        'current_search': search_query if search_query and search_query != 'None' else '',
        # Summary statistics for cards
        'total_vehicles': total_vehicles,
        'available_vehicles': available_vehicles,
        'rented_vehicles': rented_vehicles,
        'maintenance_vehicles': maintenance_vehicles,
    }
    
    return render(request, 'vehicle_rental/vehicle_list.html', context)


@login_required
def rental_calendar(request):
    """Calendar view showing confirmed and pending rentals with vehicle/month filters"""
    
    # Get filter parameters
    vehicle_filter = request.GET.get('vehicle')
    year = request.GET.get('year', datetime.now().year)
    month = request.GET.get('month', datetime.now().month)
    
    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        year = datetime.now().year
        month = datetime.now().month
    
    # Get confirmed and pending rentals for the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Filter rentals
    rentals = Rental.objects.filter(
        status__in=['confirmed', 'pending'],
        start_date__lte=end_date,
        end_date__gte=start_date
    ).select_related('vehicle', 'customer').order_by('start_date')
    
    if vehicle_filter and vehicle_filter != '':
        rentals = rentals.filter(vehicle_id=vehicle_filter)
    
    # Build calendar data
    cal = calendar.Calendar()
    month_days = list(cal.itermonthdays(year, month))
    
    # Group rentals by date
    rental_dict = {}
    for rental in rentals:
        # Convert datetime to date for comparison
        rental_start = rental.start_date.date() if hasattr(rental.start_date, 'date') else rental.start_date
        rental_end = rental.end_date.date() if hasattr(rental.end_date, 'date') else rental.end_date
        
        current_date = rental_start
        while current_date <= rental_end:
            if start_date <= current_date <= end_date:
                if current_date not in rental_dict:
                    rental_dict[current_date] = []
                rental_dict[current_date].append(rental)
            current_date += timedelta(days=1)
    
    # Create calendar structure
    weeks = []
    week = []
    
    for day in month_days:
        if day == 0:
            week.append(None)
        else:
            day_date = date(year, month, day)
            day_rentals = rental_dict.get(day_date, [])
            week.append({
                'day': day,
                'date': day_date,
                'rentals': day_rentals,
                'has_confirmed': any(r.status == 'confirmed' for r in day_rentals),
                'has_pending': any(r.status == 'pending' for r in day_rentals)
            })
        
        if len(week) == 7:
            weeks.append(week)
            week = []
    
    if week:
        weeks.append(week)
    
    # Navigation dates
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    # Filter options
    vehicles = Vehicle.objects.filter(is_active=True).order_by('brand__name', 'model')
    month_name = calendar.month_name[month]
    
    context = {
        'weeks': weeks,
        'current_year': year,
        'current_month': month,
        'current_month_name': month_name,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'vehicles': vehicles,
        'current_vehicle': vehicle_filter,
        'rentals': rentals
    }
    
    return render(request, 'vehicle_rental/rental_calendar.html', context)


@login_required
def vehicle_detail(request, pk):
    """Vehicle detail view with rental history and maintenance records"""
    
    vehicle = get_object_or_404(Vehicle, pk=pk)
    
    # Rental history
    rentals = vehicle.rentals.select_related('customer').order_by('-start_date')[:10]
    
    # Maintenance history
    maintenance_records = vehicle.maintenance_records.order_by('-date_scheduled')[:10]
    
    # Recent expenses
    expenses = vehicle.expenses.select_related('category').order_by('-date')[:10]
    
    # Current rental
    current_rental = vehicle.get_current_rental()
    
    context = {
        'vehicle': vehicle,
        'rentals': rentals,
        'maintenance_records': maintenance_records,
        'expenses': expenses,
        'current_rental': current_rental,
    }
    
    return render(request, 'vehicle_rental/vehicle_detail.html', context)


@login_required
def vehicle_create(request):
    """Create a new vehicle"""
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.created_by = request.user
            vehicle.save()
            
            # Handle multiple additional photos
            additional_photos = request.FILES.getlist('additional_photos')
            photos_created = 0
            
            for i, photo_file in enumerate(additional_photos):
                # Get photo metadata
                photo_type = request.POST.get(f'photo_type_{i}', 'other')
                title = request.POST.get(f'title_{i}', f'Photo {i+1}')
                description = request.POST.get(f'description_{i}', '')
                is_primary = request.POST.get(f'is_primary_{i}', 'off') == 'on' if i == 0 else False
                
                # Create VehiclePhoto instance
                VehiclePhoto.objects.create(
                    vehicle=vehicle,
                    image=photo_file,
                    photo_type=photo_type,
                    title=title,
                    description=description,
                    is_primary=is_primary,
                    uploaded_by=request.user
                )
                photos_created += 1
            
            success_msg = f'Vehicle {vehicle.registration_number} created successfully!'
            if photos_created > 0:
                success_msg += f' {photos_created} additional photos were uploaded.'
            
            messages.success(request, success_msg)
            return redirect('vehicle_rental:vehicle_detail', pk=vehicle.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = VehicleForm()
    
    # Get brands for reference
    brands = VehicleBrand.objects.all().order_by('name')
    
    context = {
        'form': form,
        'brands': brands,
        'title': 'Create New Vehicle',
    }
    
    return render(request, 'vehicle_rental/vehicle_form.html', context)


@login_required
def vehicle_edit(request, pk):
    """Edit an existing vehicle"""
    
    vehicle = get_object_or_404(Vehicle, pk=pk)
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES, instance=vehicle)
        if form.is_valid():
            vehicle = form.save()
            
            # Handle multiple additional photos
            additional_photos = request.FILES.getlist('additional_photos')
            photos_created = 0
            
            for i, photo_file in enumerate(additional_photos):
                # Get photo metadata
                photo_type = request.POST.get(f'photo_type_{i}', 'other')
                title = request.POST.get(f'title_{i}', f'Photo {i+1}')
                description = request.POST.get(f'description_{i}', '')
                is_primary = request.POST.get(f'is_primary_{i}', 'off') == 'on'
                
                # If this is marked as primary, unset other primary photos
                if is_primary:
                    VehiclePhoto.objects.filter(vehicle=vehicle, is_primary=True).update(is_primary=False)
                
                # Create VehiclePhoto instance
                VehiclePhoto.objects.create(
                    vehicle=vehicle,
                    image=photo_file,
                    photo_type=photo_type,
                    title=title,
                    description=description,
                    is_primary=is_primary,
                    uploaded_by=request.user
                )
                photos_created += 1
            
            success_msg = f'Vehicle {vehicle.registration_number} updated successfully!'
            if photos_created > 0:
                success_msg += f' {photos_created} additional photos were added.'
            
            messages.success(request, success_msg)
            return redirect('vehicle_rental:vehicle_detail', pk=vehicle.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = VehicleForm(instance=vehicle)
    
    # Get brands for reference
    brands = VehicleBrand.objects.all().order_by('name')
    
    context = {
        'form': form,
        'vehicle': vehicle,
        'brands': brands,
        'title': f'Edit Vehicle - {vehicle.registration_number}',
    }
    
    return render(request, 'vehicle_rental/vehicle_form.html', context)


@login_required
def customer_list(request):
    """List all customers with search and pagination"""
    
    customers = Customer.objects.all()
    
    # Summary statistics for cards (before filtering)
    all_customers = Customer.objects.all()
    total_customers = all_customers.count()
    active_customers = all_customers.filter(is_blacklisted=False).count()
    blacklisted_customers = all_customers.filter(is_blacklisted=True).count()
    
    # License expiry statistics
    today = timezone.now().date()
    from datetime import timedelta
    warning_date = today + timedelta(days=30)  # 30 days warning
    expired_licenses = all_customers.filter(license_expiry_date__lt=today).count()
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    license_status_filter = request.GET.get('license_status', '')
    
    # Search
    if search_query:
        customers = customers.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(id_number__icontains=search_query) |
            Q(driving_license_number__icontains=search_query)
        )
    
    # Filter by status
    if status_filter == 'active':
        customers = customers.filter(is_blacklisted=False)
    elif status_filter == 'blacklisted':
        customers = customers.filter(is_blacklisted=True)
    
    # Filter by license status
    if license_status_filter == 'valid':
        customers = customers.filter(license_expiry_date__gte=today)
    elif license_status_filter == 'expired':
        customers = customers.filter(license_expiry_date__lt=today)
    
    # Pagination
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'current_filters': {
            'search': search_query,
            'status': status_filter,
            'license_status': license_status_filter,
        },
        'today': today,
        'warning_date': warning_date,
        # Summary statistics for cards
        'total_customers': total_customers,
        'active_customers': active_customers,
        'blacklisted_customers': blacklisted_customers,
        'expired_licenses': expired_licenses,
    }
    
    return render(request, 'vehicle_rental/customer_list.html', context)


@login_required
def customer_detail(request, pk):
    """Customer detail view with rental history"""
    
    customer = get_object_or_404(Customer, pk=pk)
    
    # Rental history
    rentals = customer.rentals.select_related('vehicle', 'vehicle__brand').order_by('-start_date')
    
    # Statistics
    total_rentals = rentals.count()
    total_spent = rentals.filter(status__in=['confirmed', 'active', 'completed']).aggregate(total=Sum('total_amount'))['total'] or 0
    current_rentals = rentals.filter(status='active')
    
    # Add date variables for license expiry checks
    today = timezone.now().date()
    warning_date = today + timedelta(days=30)  # 30 days warning
    
    context = {
        'customer': customer,
        'rentals': rentals,
        'total_rentals': total_rentals,
        'total_spent': total_spent,
        'current_rentals': current_rentals,
        'today': today,
        'warning_date': warning_date,
    }
    
    return render(request, 'vehicle_rental/customer_detail.html', context)


@login_required
def customer_create(request):
    """Create new customer"""
    
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()

            # Send welcome email
            try:
                _send_welcome_email(customer, request)
            except Exception as e:
                logger.error(f'Failed to send welcome email for customer #{customer.id}: {str(e)}')
                # Don't prevent customer creation if email fails
            
            messages.success(request, f'Customer "{customer.full_name}" has been created successfully!')
            return redirect('vehicle_rental:customer_detail', pk=customer.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = CustomerForm()
    
    context = {
        'form': form,
        'title': 'Registar Novo Cliente',
        'submit_text': 'Registar'
    }
    
    return render(request, 'vehicle_rental/customer_form.html', context)


@login_required
def customer_edit(request, pk):
    """Edit existing customer"""
    
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.full_name}" has been updated successfully!')
            return redirect('vehicle_rental:customer_detail', pk=customer.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = CustomerForm(instance=customer)
    
    context = {
        'form': form,
        'customer': customer,
        'title': f'Edit Customer - {customer.full_name}',
        'submit_text': 'Update Customer'
    }
    
    return render(request, 'vehicle_rental/customer_form.html', context)


@login_required
def rental_list(request):
    """List all rentals with filtering"""
    
    rentals = Rental.objects.select_related('customer', 'vehicle', 'vehicle__brand')
    
    # Summary statistics for cards (before filtering)
    all_rentals = Rental.objects.select_related('customer', 'vehicle', 'vehicle__brand')
    total_rentals = all_rentals.count()
    active_rentals = all_rentals.filter(status='active').count()
    completed_rentals = all_rentals.filter(status='completed').count()
    pending_rentals = all_rentals.filter(status='pending').count()
    
    # Get filter parameters
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to') 
    search_query = request.GET.get('search')
    
    # Apply filters
    if status_filter and status_filter.strip() and status_filter != 'None':
        rentals = rentals.filter(status=status_filter)
    
    if date_from and date_from.strip() and date_from != 'None':
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            rentals = rentals.filter(start_date__date__gte=from_date)
        except ValueError:
            pass
    
    if date_to and date_to.strip() and date_to != 'None':
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            rentals = rentals.filter(end_date__date__lte=to_date)
        except ValueError:
            pass
    
    if search_query and search_query.strip() and search_query != 'None':
        rentals = rentals.filter(
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(vehicle__registration_number__icontains=search_query) |
            Q(vehicle__brand__name__icontains=search_query) |
            Q(vehicle__model__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # Order by most recent
    rentals = rentals.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(rentals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_choices': Rental.STATUS_CHOICES,
        'current_filters': {
            'status': status_filter if status_filter and status_filter != 'None' else '',
            'date_from': date_from if date_from and date_from != 'None' else '',
            'date_to': date_to if date_to and date_to != 'None' else '',
            'search': search_query if search_query and search_query != 'None' else '',
        },
        # Summary statistics for cards
        'total_rentals': total_rentals,
        'active_rentals': active_rentals,
        'completed_rentals': completed_rentals,
        'pending_rentals': pending_rentals,
    }
    
    return render(request, 'vehicle_rental/rental_list.html', context)


@login_required
def rental_detail(request, pk):
    """Rental detail view"""
    
    rental = get_object_or_404(
        Rental.objects.select_related('customer', 'vehicle', 'vehicle__brand'),
        pk=pk
    )
    
    # Fix empty total_amount if needed
    if not rental.total_amount and rental.daily_rate and rental.number_of_days:
        rental.subtotal = rental.daily_rate * rental.number_of_days
        rental.commission_amount = (rental.subtotal * rental.commission_percent) / 100
        rental.total_amount = (
            rental.subtotal - 
            rental.commission_amount + 
            (rental.insurance_fee or 0) + 
            (rental.late_return_fee or 0) + 
            (rental.damage_fee or 0)
        )
        rental.save()
    
    # Related expenses
    expenses = rental.expenses.select_related('category').order_by('-date')
    
    # Evaluation (if exists)
    evaluation = None
    try:
        if hasattr(rental, 'evaluation'):
            evaluation = rental.evaluation
    except RentalEvaluation.DoesNotExist:
        evaluation = None
    
    # Photo counts by stage
    start_photos_count = rental.photos.filter(
        photo_type__startswith='start_'
    ).count()
    
    return_photos_count = rental.photos.filter(
        photo_type__startswith='return_'
    ).count()
    
    context = {
        'rental': rental,
        'expenses': expenses,
        'evaluation': evaluation,
        'start_photos_count': start_photos_count,
        'return_photos_count': return_photos_count,
    }
    
    return render(request, 'vehicle_rental/rental_detail.html', context)


@login_required
def rental_create(request):
    """Create new rental"""
    # Get vehicle_id and customer_id from URL parameters if provided
    vehicle_id = request.GET.get('vehicle')
    customer_id = request.GET.get('customer')
    initial_data = {}
    if vehicle_id:
        initial_data['vehicle'] = vehicle_id
    if customer_id:
        initial_data['customer'] = customer_id
    
    # Pre-populate commission from SystemConfiguration
    sys_config = SystemConfiguration.get_instance()
    if 'commission_percent' not in initial_data and 'commission_amount' not in initial_data:
        if sys_config.service_fee_percentage is not None:
            initial_data['commission_percent'] = sys_config.service_fee_percentage
        elif sys_config.service_fee_amount is not None:
            initial_data['commission_amount'] = sys_config.service_fee_amount
    
    if request.method == 'POST':
        form = RentalForm(request.POST, initial=initial_data)
        if form.is_valid():
            rental = form.save(commit=False)
            rental.created_by = request.user
            rental.save()
            
            # Send booking notification email
            try:
                _send_rental_booking_email(rental, request)
            except Exception as e:
                logger.error(f'Failed to send booking email for rental #{rental.id}: {str(e)}')
                # Don't prevent rental creation if email fails
            
            # Vehicle status will be updated automatically by signals
            
            messages.success(request, 'Rental created successfully!')
            return redirect('vehicle_rental:rental_detail', pk=rental.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = RentalForm(initial=initial_data)
    
    context = {
        'form': form,
        'available_vehicles': Vehicle.objects.filter(is_active=True),
        'customers': Customer.objects.filter(is_blacklisted=False),
        'sys_config': sys_config,
    }
    
    return render(request, 'vehicle_rental/rental_create.html', context)


@login_required
def rental_edit(request, pk):
    """Edit existing rental"""
    
    rental = get_object_or_404(Rental, pk=pk)
    
    if request.method == 'POST':
        form = RentalForm(request.POST, instance=rental)
        if form.is_valid():
            rental = form.save()
            messages.success(request, f'Rental #{rental.id} has been updated successfully!')
            return redirect('vehicle_rental:rental_detail', pk=rental.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = RentalForm(instance=rental)
        # For editing, we need to include all vehicles (including the currently rented one)
        form.fields['vehicle'].queryset = Vehicle.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'rental': rental,
        'available_vehicles': Vehicle.objects.filter(is_active=True),
        'customers': Customer.objects.filter(is_blacklisted=False),
        'sys_config': SystemConfiguration.get_instance(),
    }
    
    return render(request, 'vehicle_rental/rental_create.html', context)


def _send_rental_booking_email(rental, request):
    """Send booking email with tracking link to customer after rental creation."""
    customer = rental.customer
    if not customer.email:
        logger.warning('Rental #%s: customer has no email, skipping booking notification.', rental.id)
        return

    subject = f'Nova Reserva #{rental.id} - {rental.vehicle.brand.name} {rental.vehicle.model}'

    # Generate tracking URL for customer to check booking status
    booking_status_url = os.environ.get('BOOKING_STATUS_URL', 'http://localhost:8080/universal-rent-a-car/booking-status')
    tracking_url = f"{booking_status_url}?rental_id={rental.id}"

    context = {
        'rental': rental,
        'tracking_url': tracking_url,
        'company_name': 'Universal Rent a Car',
        'company_email': 'universal.r.car@gmail.com',
        'company_phone1': '(+238) 978 13 04',
        'company_phone2': '(+238) 347 6581',
    }

    html_body = render_to_string('vehicle_rental/email/rental_booking.html', context)
    # Plain-text fallback
    text_body = (
        f'Olá {customer.full_name},\n\n'
        f'A sua reserva #{rental.id} foi criada com sucesso.\n'
        f'Veículo: {rental.vehicle.brand.name} {rental.vehicle.model} ({rental.vehicle.year})\n'
        f'Período: {rental.start_date:%d/%m/%Y} - {rental.end_date:%d/%m/%Y}\n'
        f'Status: Pendente de Confirmação\n\n'
        f'Acompanhe sua reserva em: {tracking_url}\n\n'
        f'Obrigado!'
    )

    # Create notification record
    notification = CustomerNotification.objects.create(
        customer=customer,
        rental=rental,
        notification_type='rental_booking',
        recipient_email=customer.email,
        subject=subject,
        content=text_body,
        html_content=html_body,
        status='pending'
    )
    
    # Attempt to send
    success, error_msg = notification.send()
    
    if not success:
        logger.error(f'Rental #{rental.id}: failed to send booking email - {error_msg}')


def _send_rental_confirmation_email(rental):
    """Send confirmation email with reservation details and invoice to customer."""
    customer = rental.customer
    if not customer.email:
        logger.warning('Rental #%s: customer has no email, skipping notification.', rental.id)
        return

    # Calculate commission value for percentage-based commission
    commission_value = 0
    if rental.commission_percent and rental.base_amount:
        commission_value = (rental.base_amount * rental.commission_percent) / 100

    subject = f'Confirmação de Reserva #{rental.id} - {rental.vehicle.brand.name} {rental.vehicle.model}'

    context = {
        'rental': rental,
        'commission_value': commission_value,
        'company_name': 'Universal Rent a Car',
        'company_email': 'universal.r.car@gmail.com',
        'company_phone1': '(+238) 978 13 04',
        'company_phone2': '(+238) 347 6581',
    }

    html_body = render_to_string('vehicle_rental/email/rental_confirmation.html', context)
    # Plain-text fallback
    text_body = (
        f'Olá {customer.full_name},\n\n'
        f'A sua reserva #{rental.id} foi confirmada.\n'
        f'Veículo: {rental.vehicle.brand.name} {rental.vehicle.model} ({rental.vehicle.year})\n'
        f'Período: {rental.start_date:%d/%m/%Y} - {rental.end_date:%d/%m/%Y}\n'
        f'Total: {rental.total_amount} {rental.currency}\n\n'
        f'Obrigado!'
    )

    # Create notification record
    notification = CustomerNotification.objects.create(
        customer=customer,
        rental=rental,
        notification_type='rental_confirmation',
        recipient_email=customer.email,
        subject=subject,
        content=text_body,
        html_content=html_body,
        status='pending'
    )
    
    # Attempt to send
    success, error_msg = notification.send()
    
    if not success:
        logger.error(f'Rental #{rental.id}: failed to send confirmation email - {error_msg}')


def _send_rental_return_email(rental, request):
    """Send return completion email with evaluation link to customer."""
    customer = rental.customer
    if not customer.email:
        logger.warning('Rental #%s: customer has no email, skipping return notification.', rental.id)
        return

    subject = f'Devolução Concluída - Reserva #{rental.id}'

    # Generate evaluation URL for customer to rate the rental
    dashboard_url = os.environ.get('CUSTOMER_DASHBOARD_URL', 'http://localhost:8080/universal-rent-a-car/owner-dashboard')
    evaluation_url = f"{dashboard_url}?tab=my-bookings"

    context = {
        'rental': rental,
        'evaluation_url': evaluation_url,
        'company_name': 'Universal Rent a Car',
        'company_email': 'universal.r.car@gmail.com',
        'company_phone1': '(+238) 978 13 04',
        'company_phone2': '(+238) 347 6581',
    }

    html_body = render_to_string('vehicle_rental/email/rental_return.html', context)
    # Plain-text fallback
    text_body = (
        f'Olá {customer.full_name},\n\n'
        f'A devolução da reserva #{rental.id} foi concluída.\n'
        f'Veículo: {rental.vehicle.brand.name} {rental.vehicle.model} ({rental.vehicle.year})\n'
        f'Data de Devolução: {rental.actual_return_date:%d/%m/%Y %H:%M}\n\n'
        f'Avalie sua experiência: {evaluation_url}\n\n'
        f'Obrigado por escolher a Universal Rent a Car!'
    )

    # Create notification record
    notification = CustomerNotification.objects.create(
        customer=customer,
        rental=rental,
        notification_type='rental_return',
        recipient_email=customer.email,
        subject=subject,
        content=text_body,
        html_content=html_body,
        status='pending'
    )
    
    # Attempt to send
    success, error_msg = notification.send()
    
    if not success:
        logger.error(f'Rental #{rental.id}: failed to send return email - {error_msg}')


def _send_rental_cancellation_email(rental):
    """Send cancellation notification email to customer."""
    customer = rental.customer
    if not customer.email:
        logger.warning('Rental #%s: customer has no email, skipping cancellation notification.', rental.id)
        return

    subject = f'Cancelamento de Reserva #{rental.id} - Universal Rent a Car'

    context = {
        'rental': rental,
        'customer': customer,
        'vehicle': rental.vehicle,
        'company_name': 'Universal Rent a Car',
        'company_email': 'universal.r.car@gmail.com',
        'company_phone1': '(+238) 978 13 04',
        'company_phone2': '(+238) 347 6581',
    }

    # Try to render HTML template if it exists, otherwise use plain text
    try:
        html_body = render_to_string('vehicle_rental/email/rental_cancellation.html', context)
    except Exception:
        html_body = None

    # Plain-text fallback
    text_body = (
        f'Olá {customer.full_name},\n\n'
        f'A sua reserva #{rental.id} foi cancelada.\n\n'
        f'Detalhes da Reserva Cancelada:\n'
        f'Veículo: {rental.vehicle.brand.name} {rental.vehicle.model} ({rental.vehicle.year})\n'
        f'Matrícula: {rental.vehicle.registration_number}\n'
        f'Período: {rental.start_date:%d/%m/%Y %H:%M} - {rental.end_date:%d/%m/%Y %H:%M}\n'
        f'Valor Total: {rental.total_amount} {rental.currency}\n\n'
        f'Se tiver alguma questão ou precisar de assistência, não hesite em contactar-nos.\n\n'
        f'Atenciosamente,\n'
        f'Universal Rent a Car\n'
        f'Tel: (+238) 978 13 04 / (+238) 347 6581\n'
        f'Email: universal.r.car@gmail.com'
    )

    # Create notification record
    notification = CustomerNotification.objects.create(
        customer=customer,
        rental=rental,
        notification_type='rental_cancellation',
        recipient_email=customer.email,
        subject=subject,
        content=text_body,
        html_content=html_body if html_body else text_body,
        status='pending'
    )
    
    # Attempt to send
    success, error_msg = notification.send()
    
    if not success:
        logger.error(f'Rental #{rental.id}: failed to send cancellation email - {error_msg}')


def _send_welcome_email(customer, request=None):
    """Send welcome email to newly registered customer."""
    if not customer.email:
        logger.warning('Customer #%s: has no email, skipping welcome notification.', customer.id)
        return

    subject = f'Bem-vindo à Universal Rent a Car!'

    # Generate portal URL
    portal_url = request.build_absolute_uri('/') if request else 'https://universalrentacar.cv'

    context = {
        'customer': customer,
        'portal_url': portal_url,
        'company_name': 'Universal Rent a Car',
        'company_email': 'universal.r.car@gmail.com',
        'company_phone1': '(+238) 978 13 04',
        'company_phone2': '(+238) 347 6581',
        'current_year': timezone.now().year,
    }

    html_body = render_to_string('vehicle_rental/email/customer_welcome.html', context)
    # Plain-text fallback
    text_body = (
        f'Olá {customer.full_name},\n\n'
        f'Bem-vindo à Universal Rent a Car!\n'
        f'Estamos felizes por tê-lo como nosso cliente.\n\n'
        f'Detalhes da Conta:\n'
        f'Nome: {customer.full_name}\n'
        f'Email: {customer.email}\n'
        f'Telefone: {customer.phone}\n\n'
        f'Acesse nosso portal: {portal_url}\n\n'
        f'Obrigado por escolher a Universal Rent a Car!'
    )

    # Create notification record
    notification = CustomerNotification.objects.create(
        customer=customer,
        rental=None,
        notification_type='customer_welcome',
        recipient_email=customer.email,
        subject=subject,
        content=text_body,
        html_content=html_body,
        status='pending'
    )
    
    # Attempt to send
    success, error_msg = notification.send()
    
    if not success:
        logger.error(f'Customer #{customer.id}: failed to send welcome email - {error_msg}')


@login_required
def rental_confirm(request, pk):
    """Confirm a pending rental"""
    rental = get_object_or_404(Rental, pk=pk)
    
    if request.method == 'POST':
        if rental.status == 'pending':
            rental.status = 'confirmed'
            rental.save()
            
            # Vehicle status will be updated automatically by signals
            
            # Send confirmation email to customer
            _send_rental_confirmation_email(rental)
            
            messages.success(request, f'Aluguer #{rental.id} foi confirmado com sucesso!')
        else:
            messages.error(request, 'Apenas alugueres pendentes podem ser confirmados.')
        
        return redirect('vehicle_rental:rental_detail', pk=rental.pk)
    
    context = {
        'rental': rental,
        'action': 'confirmar'
    }
    return render(request, 'vehicle_rental/rental_confirm_action.html', context)


@login_required
def rental_cancel(request, pk):
    """Cancel a rental"""
    rental = get_object_or_404(Rental, pk=pk)
    
    if request.method == 'POST':
        if rental.status in ['pending', 'confirmed']:
            rental.status = 'cancelled'
            rental.save()
            
            # Vehicle status will be updated automatically by signals
            
            # Send cancellation notification email
            try:
                _send_rental_cancellation_email(rental)
            except Exception as e:
                logger.error(f"Failed to send cancellation email for rental {rental.id}: {str(e)}")
            
            messages.success(request, f'Aluguer #{rental.id} foi cancelado com sucesso!')
        else:
            messages.error(request, 'Apenas alugueres pendentes ou confirmados podem ser cancelados.')
        
        return redirect('vehicle_rental:rental_detail', pk=rental.pk)
    
    context = {
        'rental': rental,
        'action': 'cancelar'
    }
    return render(request, 'vehicle_rental/rental_confirm_action.html', context)


@login_required
def rental_return(request, pk):
    """Register the actual return date and complete the rental"""
    rental = get_object_or_404(Rental, pk=pk)
    
    if request.method == 'POST':
        if rental.status in ['confirmed', 'active']:
            # Get return details from form
            actual_return_date = request.POST.get('actual_return_date')
            mileage_end = request.POST.get('mileage_end')
            fuel_level_end = request.POST.get('fuel_level_end')
            condition_return = request.POST.get('condition_return')
            notes = request.POST.get('return_notes', '')
            late_return_fee = request.POST.get('late_return_fee', '')
            damage_fee = request.POST.get('damage_fee', '0')
            
            # Validate inputs
            if not actual_return_date:
                messages.error(request, 'Data de devolução é obrigatória.')
                context = {
                    'rental': rental,
                    'fuel_choices': [
                        ('empty', 'Vazio'),
                        ('quarter', '1/4'),
                        ('half', '1/2'),
                        ('three_quarter', '3/4'),
                        ('full', 'Cheio')
                    ],
                    'form_data': request.POST  # Preserve form data
                }
                return render(request, 'vehicle_rental/rental_return.html', context)
            
            try:
                from datetime import datetime
                return_datetime = datetime.strptime(actual_return_date, '%Y-%m-%dT%H:%M')
                
                # Validate return date is not before start date
                if return_datetime.date() < rental.start_date.date():
                    messages.error(request, f'A data de devolução não pode ser anterior à data de início do aluguer ({rental.start_date.strftime("%d/%m/%Y")}).')
                    context = {
                        'rental': rental,
                        'fuel_choices': [
                            ('empty', 'Vazio'),
                            ('quarter', '1/4'),
                            ('half', '1/2'),
                            ('three_quarter', '3/4'),
                            ('full', 'Cheio')
                        ],
                        'form_data': request.POST  # Preserve form data
                    }
                    return render(request, 'vehicle_rental/rental_return.html', context)
                
                # Update rental details
                rental.actual_return_date = return_datetime
                rental.status = 'completed'
                
                if mileage_end:
                    rental.mileage_end = float(mileage_end)
                
                if fuel_level_end:
                    rental.fuel_level_return = fuel_level_end
                
                if condition_return:
                    rental.condition_return = condition_return
                
                # Handle fees
                if late_return_fee != '':  # If late_return_fee was provided (including '0')
                    rental.late_return_fee = Decimal(late_return_fee)
                elif return_datetime.date() > rental.end_date.date():
                    # Auto-calculate late fees only if no manual input was provided and overdue
                    days_late = (return_datetime.date() - rental.end_date.date()).days
                    auto_late_fee = rental.daily_rate * Decimal('0.1') * days_late  # 10% of daily rate per day late
                    rental.late_return_fee = auto_late_fee
                else:
                    # Not overdue and no manual input, keep existing value or set to 0
                    if rental.late_return_fee is None:
                        rental.late_return_fee = Decimal('0')
                
                if damage_fee:
                    rental.damage_fee = Decimal(damage_fee)
                
                if notes:
                    rental.notes = (rental.notes or '') + f'\nDevolução: {notes}'
                
                rental.save()
                
                # Send return completion notification email
                try:
                    _send_rental_return_email(rental, request)
                except Exception as e:
                    logger.error(f'Failed to send return email for rental #{rental.id}: {str(e)}')
                    # Don't prevent return completion if email fails
                
                # Vehicle status will be updated automatically by signals
                
                messages.success(request, f'Devolução do Aluguer #{rental.id} registada com sucesso!')
                return redirect('vehicle_rental:rental_detail', pk=rental.pk)
                
            except ValueError:
                messages.error(request, 'Formato de data inválido.')
                context = {
                    'rental': rental,
                    'fuel_choices': [
                        ('empty', 'Vazio'),
                        ('quarter', '1/4'),
                        ('half', '1/2'),
                        ('three_quarter', '3/4'),
                        ('full', 'Cheio')
                    ],
                    'form_data': request.POST  # Preserve form data
                }
                return render(request, 'vehicle_rental/rental_return.html', context)
        else:
            messages.error(request, 'Apenas alugueres confirmados ou ativos podem ser devolvidos.')
            return redirect('vehicle_rental:rental_detail', pk=rental.pk)
    
    context = {
        'rental': rental,
        'fuel_choices': [
            ('empty', 'Vazio'),
            ('quarter', '1/4'),
            ('half', '1/2'),
            ('three_quarter', '3/4'),
            ('full', 'Cheio')
        ]
    }
    return render(request, 'vehicle_rental/rental_return.html', context)


@login_required
def rental_photos(request, pk):
    """Manage rental photos for start and return stages"""
    rental = get_object_or_404(Rental, pk=pk)
    stage = request.GET.get('stage', 'start')  # 'start' or 'return'
    
    # Get existing photos for both stages
    start_photos = rental.photos.filter(photo_type__startswith='start_')
    return_photos = rental.photos.filter(photo_type__startswith='return_')
    
    # Choose appropriate photos based on stage
    if stage == 'start':
        existing_photos = start_photos
    else:
        existing_photos = return_photos

    if request.method == 'POST':
        # Handle individual photo deletion
        delete_photo_id = request.POST.get('delete_photo_id')
        if delete_photo_id:
            try:
                photo_to_delete = RentalPhoto.objects.get(
                    id=delete_photo_id, 
                    rental=rental
                )
                photo_type_display = photo_to_delete.get_photo_type_display()
                photo_to_delete.delete()
                messages.success(request, f'Foto "{photo_type_display}" foi apagada com sucesso!')
                print(f"Successfully deleted individual photo: {delete_photo_id}")
            except RentalPhoto.DoesNotExist:
                messages.error(request, 'Foto não encontrada.')
                print(f"Photo not found for deletion: {delete_photo_id}")
            except Exception as e:
                messages.error(request, f'Erro ao apagar foto: {e}')
                print(f"Error deleting individual photo {delete_photo_id}: {e}")
            
            # Redirect to refresh the page
            redirect_url = reverse('vehicle_rental:rental_photos', kwargs={'pk': rental.pk}) + f'?stage={stage}'
            return HttpResponseRedirect(redirect_url)
        
        # Handle single photo upload
        photo_type = request.POST.get('photo_type')
        image = request.FILES.get('image')
        description = request.POST.get('description', '')
        
        print(f"=== SINGLE PHOTO UPLOAD DEBUG ===")
        print(f"Photo type: {photo_type}")
        print(f"Image: {image}")
        print(f"Description: {description}")
        print(f"Stage: {stage}")
        
        if photo_type and image:
            try:
                # Check if photo type already exists
                existing_photo = RentalPhoto.objects.filter(
                    rental=rental,
                    photo_type=photo_type
                ).first()
                
                if existing_photo:
                    # Update existing photo
                    existing_photo.image = image
                    existing_photo.description = description
                    existing_photo.taken_by = request.user
                    existing_photo.save()
                    messages.success(request, f'Foto "{existing_photo.get_photo_type_display()}" foi atualizada com sucesso!')
                    print(f"Updated existing photo: {existing_photo.id}")
                else:
                    # Create new photo
                    new_photo = RentalPhoto.objects.create(
                        rental=rental,
                        photo_type=photo_type,
                        image=image,
                        description=description,
                        taken_by=request.user
                    )
                    messages.success(request, f'Foto "{new_photo.get_photo_type_display()}" foi adicionada com sucesso!')
                    print(f"Created new photo: {new_photo.id} - {new_photo.photo_type}")
                
                # Redirect to refresh the page and show the new photo
                redirect_url = reverse('vehicle_rental:rental_photos', kwargs={'pk': rental.pk}) + f'?stage={stage}'
                return HttpResponseRedirect(redirect_url)
                
            except Exception as e:
                messages.error(request, f'Erro ao guardar foto: {e}')
                print(f"Error saving photo: {e}")
        else:
            messages.error(request, 'Por favor, selecione um tipo de foto e uma imagem.')
            print("Missing photo_type or image")

    context = {
        'rental': rental,
        'stage': stage,
        'existing_photos': existing_photos,
        'start_photos_count': start_photos.count(),
        'return_photos_count': return_photos.count(),
    }
    
    print(f"=== CONTEXT DEBUG ===")
    print(f"Stage: {stage}")
    print(f"Existing photos count: {existing_photos.count()}")
    print(f"Start photos count: {start_photos.count()}")
    print(f"Return photos count: {return_photos.count()}")
    
    return render(request, 'vehicle_rental/rental_photos.html', context)
@login_required
def expense_list(request):
    """List all expenses with filtering"""
    
    expenses = Expense.objects.select_related('vehicle', 'category', 'rental')
    
    # Calculate summary statistics before filtering
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    pending_expenses = expenses.filter(is_approved=False).aggregate(total=Sum('amount'))['total'] or 0
    approved_expenses = expenses.filter(is_approved=True).aggregate(total=Sum('amount'))['total'] or 0
    rejected_expenses = 0  # Assuming you have a rejected status field, adjust as needed
    
    # Filtering
    vehicle_filter = request.GET.get('vehicle')
    category_filter = request.GET.get('category')
    approved_filter = request.GET.get('approved')
    
    if vehicle_filter:
        expenses = expenses.filter(vehicle_id=vehicle_filter)
    
    if category_filter:
        expenses = expenses.filter(category_id=category_filter)
    
    if approved_filter == 'true':
        expenses = expenses.filter(is_approved=True)
    elif approved_filter == 'false':
        expenses = expenses.filter(is_approved=False)
    
    # Order by most recent
    expenses = expenses.order_by('-date')
    
    # Pagination
    paginator = Paginator(expenses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': ExpenseCategory.objects.all().order_by('name'),
        'vehicles': Vehicle.objects.all().order_by('registration_number'),
        'summary': {
            'total_amount': total_expenses,
            'pending_amount': pending_expenses,
            'approved_amount': approved_expenses,
            'rejected_amount': rejected_expenses,
        },
        'current_filters': {
            'vehicle': vehicle_filter,
            'category': category_filter,
            'approved': approved_filter,
        }
    }
    
    return render(request, 'vehicle_rental/expense_list.html', context)


@login_required
def expense_export_invoice(request):
    """Export expense list as PDF invoice"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import cm
        from django.http import HttpResponse
        from datetime import datetime
        import io
        
        # Get filtered expenses (same logic as expense_list view)
        expenses = Expense.objects.select_related('vehicle', 'category', 'rental')
        
        # Apply same filters as the list view
        vehicle_filter = request.GET.get('vehicle')
        category_filter = request.GET.get('category')
        approved_filter = request.GET.get('approved')
        search_filter = request.GET.get('search')
        
        if vehicle_filter:
            expenses = expenses.filter(vehicle_id=vehicle_filter)
        
        if category_filter:
            expenses = expenses.filter(category_id=category_filter)
        
        if approved_filter == 'true':
            expenses = expenses.filter(is_approved=True)
        elif approved_filter == 'false':
            expenses = expenses.filter(is_approved=False)
        
        if search_filter:
            from django.db.models import Q
            expenses = expenses.filter(
                Q(description__icontains=search_filter) |
                Q(vendor__icontains=search_filter) |
                Q(vehicle__registration_number__icontains=search_filter) |
                Q(vehicle__brand__name__icontains=search_filter) |
                Q(vehicle__model__icontains=search_filter)
            )
        
        # Order by date
        expenses = expenses.order_by('date')
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.darkblue,
            alignment=1,  # Center alignment
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
        )
        
        # Create a smaller text style for table content
        table_text_style = ParagraphStyle(
            'TableText',
            parent=styles['Normal'],
            fontSize=7,
            leading=8,
            leftIndent=0,
            rightIndent=0,
            spaceAfter=0,
            spaceBefore=0,
        )
        
        # Build content
        story = []
        
        # Header
        story.append(Paragraph("SISTEMA DE GESTÃO DE ALUGUER", title_style))
        story.append(Paragraph("Relatório de Despesas", heading_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Date and filters info
        filter_info = []
        filter_info.append(f"<b>Data de Geração:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        if vehicle_filter:
            try:
                vehicle = Vehicle.objects.get(id=vehicle_filter)
                filter_info.append(f"<b>Veículo:</b> {vehicle.registration_number} - {vehicle.brand.name} {vehicle.model}")
            except Vehicle.DoesNotExist:
                pass
        
        if category_filter:
            try:
                category = ExpenseCategory.objects.get(id=category_filter)
                filter_info.append(f"<b>Categoria:</b> {category.name}")
            except ExpenseCategory.DoesNotExist:
                pass
        
        if approved_filter == 'true':
            filter_info.append("<b>Estado:</b> Apenas Aprovadas")
        elif approved_filter == 'false':
            filter_info.append("<b>Estado:</b> Apenas Pendentes")
        
        if search_filter:
            filter_info.append(f"<b>Pesquisa:</b> {search_filter}")
        
        for info in filter_info:
            story.append(Paragraph(info, styles['Normal']))
        
        story.append(Spacer(1, 0.5*cm))
        
        # Expense table
        if expenses.exists():
            # Table headers
            data = [
                ['Data', 'Veículo', 'Categoria', 'Descrição', 'Fornecedor', 'Estado', 'Valor (ECV)']
            ]
            
            # Table rows
            total_amount = 0
            for expense in expenses:
                status = "Aprovada" if expense.is_approved else "Pendente"
                
                # Create wrapped text using Paragraph for columns that might overflow
                vehicle_text = f"{expense.vehicle.registration_number}"
                vehicle_para = Paragraph(vehicle_text, table_text_style)
                
                category_text = expense.category.name
                category_para = Paragraph(category_text, table_text_style)
                
                description_text = expense.description[:100] if len(expense.description) > 100 else expense.description
                description_para = Paragraph(description_text, table_text_style)
                
                vendor_text = expense.vendor or '-'
                vendor_para = Paragraph(vendor_text, table_text_style)
                
                status_para = Paragraph(status, table_text_style)
                
                data.append([
                    expense.date.strftime('%d/%m/%Y'),
                    vehicle_para,
                    category_para,
                    description_para,
                    vendor_para,
                    status_para,
                    f"{expense.amount:,.2f}"
                ])
                total_amount += expense.amount
            
            # Create table with optimized column widths
            table = Table(data, colWidths=[1.8*cm, 2*cm, 2*cm, 5.5*cm, 2*cm, 1.5*cm, 2.2*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (3, 1), (3, -1), 'LEFT'),  # Description column left-aligned
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Vehicle column left-aligned
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),  # Category column left-aligned
                ('ALIGN', (4, 1), (4, -1), 'LEFT'),  # Vendor column left-aligned
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Top alignment for better text wrapping
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.5*cm))
            
            # Summary
            summary_data = [
                ['Total de Despesas:', f"{len(expenses)} items"],
                ['Valor Total:', f"{total_amount:,.2f} ECV"],
            ]
            
            summary_table = Table(summary_data, colWidths=[4*cm, 3*cm])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
            ]))
            
            story.append(summary_table)
            
        else:
            story.append(Paragraph("Nenhuma despesa encontrada com os filtros aplicados.", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Create response
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f"relatorio_despesas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except ImportError as e:
        messages.error(request, f'PDF generation requires ReportLab. Error: {str(e)}')
        return redirect('vehicle_rental:expense_list')
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('vehicle_rental:expense_list')


@login_required
def expense_create(request):
    """Create a new expense"""
    # Get vehicle_id from URL parameter if provided
    vehicle_id = request.GET.get('vehicle')
    initial_data = {}
    if vehicle_id:
        initial_data['vehicle'] = vehicle_id
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, initial=initial_data)
        if form.is_valid():
            expense = form.save()
            messages.success(request, f'Expense "{expense.description[:50]}" created successfully!')
            return redirect('vehicle_rental:expense_detail', pk=expense.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = ExpenseForm(initial=initial_data)
    
    context = {
        'form': form,
        'title': 'Create Expense'
    }
    return render(request, 'vehicle_rental/expense_form.html', context)


@login_required
def expense_edit(request, pk):
    """Edit an existing expense"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            expense = form.save()
            messages.success(request, f'Expense "{expense.description[:50]}" updated successfully!')
            return redirect('vehicle_rental:expense_detail', pk=expense.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = ExpenseForm(instance=expense)
    
    context = {
        'form': form,
        'expense': expense,
        'title': 'Edit Expense'
    }
    return render(request, 'vehicle_rental/expense_form.html', context)


@login_required
def expense_detail(request, pk):
    """View expense details"""
    expense = get_object_or_404(Expense.objects.select_related('vehicle', 'category', 'rental'), pk=pk)
    
    context = {
        'expense': expense
    }
    return render(request, 'vehicle_rental/expense_detail.html', context)


@login_required
def maintenance_list(request):
    """List all maintenance records"""
    
    maintenance_records = MaintenanceRecord.objects.select_related('vehicle', 'vehicle__brand')
    
    # Calculate summary statistics before filtering
    total_records = maintenance_records.count()
    total_cost = maintenance_records.aggregate(total=Sum('total_cost'))['total'] or 0
    scheduled_count = maintenance_records.filter(status='scheduled').count()
    completed_count = maintenance_records.filter(status='completed').count()
    
    # Filtering
    vehicle_filter = request.GET.get('vehicle')
    status_filter = request.GET.get('status')
    maintenance_type_filter = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search_query = request.GET.get('search')
    
    if vehicle_filter:
        maintenance_records = maintenance_records.filter(vehicle_id=vehicle_filter)
    
    if status_filter:
        maintenance_records = maintenance_records.filter(status=status_filter)
    
    if maintenance_type_filter:
        maintenance_records = maintenance_records.filter(maintenance_type=maintenance_type_filter)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            maintenance_records = maintenance_records.filter(date_scheduled__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            maintenance_records = maintenance_records.filter(date_scheduled__lte=to_date)
        except ValueError:
            pass
    
    if search_query:
        maintenance_records = maintenance_records.filter(
            Q(service_description__icontains=search_query) |
            Q(service_provider__icontains=search_query) |
            Q(maintenance_type__icontains=search_query) |
            Q(vehicle__registration_number__icontains=search_query)
        )
    
    # Order by most recent
    maintenance_records = maintenance_records.order_by('-date_scheduled')
    
    # Pagination
    paginator = Paginator(maintenance_records, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'vehicles': Vehicle.objects.all().order_by('registration_number'),
        'status_choices': MaintenanceRecord.STATUS_CHOICES,
        'type_choices': MaintenanceRecord.MAINTENANCE_TYPES,
        'summary': {
            'total_records': total_records,
            'total_cost': total_cost,
            'scheduled_count': scheduled_count,
            'completed_count': completed_count,
        },
        'current_filters': {
            'vehicle': vehicle_filter,
            'status': status_filter,
            'type': maintenance_type_filter,
            'date_from': date_from,
            'date_to': date_to,
            'search': search_query,
        }
    }
    
    return render(request, 'vehicle_rental/maintenance_list.html', context)


@login_required
def maintenance_create(request):
    """Create new maintenance record"""
    # Get vehicle_id from URL parameter if provided
    vehicle_id = request.GET.get('vehicle')
    initial_data = {}
    if vehicle_id:
        initial_data['vehicle'] = vehicle_id
    
    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST, initial=initial_data)
        if form.is_valid():
            maintenance = form.save(commit=False)
            maintenance.created_by = request.user
            # Ensure cost fields are not None
            maintenance.labor_cost = maintenance.labor_cost or 0
            maintenance.parts_cost = maintenance.parts_cost or 0
            maintenance.other_costs = maintenance.other_costs or 0
            # Calculate total cost
            maintenance.total_cost = maintenance.labor_cost + maintenance.parts_cost + maintenance.other_costs
            maintenance.save()
            messages.success(request, f'Maintenance record for {maintenance.vehicle.registration_number} created successfully!')
            return redirect('vehicle_rental:maintenance_detail', pk=maintenance.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = MaintenanceRecordForm(initial=initial_data)
    
    context = {
        'form': form,
        'title': 'Criar Registro de Manutenção',
        'submit_text': 'Criar Registro'
    }
    
    return render(request, 'vehicle_rental/maintenance_form.html', context)


@login_required
def maintenance_edit(request, pk):
    """Edit existing maintenance record"""
    
    maintenance = get_object_or_404(MaintenanceRecord, pk=pk)
    
    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST, instance=maintenance)
        if form.is_valid():
            maintenance = form.save(commit=False)
            # Ensure cost fields are not None
            maintenance.labor_cost = maintenance.labor_cost or 0
            maintenance.parts_cost = maintenance.parts_cost or 0
            maintenance.other_costs = maintenance.other_costs or 0
            # Calculate total cost
            maintenance.total_cost = maintenance.labor_cost + maintenance.parts_cost + maintenance.other_costs
            maintenance.save()
            messages.success(request, f'Maintenance record for {maintenance.vehicle.registration_number} updated successfully!')
            return redirect('vehicle_rental:maintenance_detail', pk=maintenance.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = MaintenanceRecordForm(instance=maintenance)
    
    context = {
        'form': form,
        'maintenance': maintenance,
        'title': f'Edit Maintenance Record - {maintenance.vehicle.registration_number}',
        'submit_text': 'Update Record'
    }
    
    return render(request, 'vehicle_rental/maintenance_form.html', context)


@login_required
def maintenance_detail(request, pk):
    """View maintenance record details"""
    
    maintenance = get_object_or_404(
        MaintenanceRecord.objects.select_related('vehicle', 'vehicle__brand'),
        pk=pk
    )
    
    context = {
        'maintenance': maintenance
    }
    
    return render(request, 'vehicle_rental/maintenance_detail.html', context)


# Reports Views
@login_required
def reports_dashboard(request):
    """Comprehensive reports dashboard with analytics"""
    from django.db.models import Sum, Count, Avg, Q, F
    from django.utils import timezone
    from datetime import datetime, timedelta
    import calendar
    
    # Get filter parameters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    period = request.GET.get('period')
    
    # Set default date range if not provided
    today = timezone.now().date()
    if period:
        if period == 'today':
            date_from = date_to = today
        elif period == 'week':
            date_from = today - timedelta(days=7)
            date_to = today
        elif period == 'month':
            date_from = today.replace(day=1)
            date_to = today
        elif period == 'quarter':
            quarter = (today.month - 1) // 3
            date_from = today.replace(month=quarter * 3 + 1, day=1)
            date_to = today
        elif period == 'year':
            date_from = today.replace(month=1, day=1)
            date_to = today
    else:
        # Default to current month if no filters
        if not date_from:
            date_from = today.replace(day=1)
        else:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        if not date_to:
            date_to = today
        else:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # Base querysets with date filtering
    rentals_qs = Rental.objects.filter(
        start_date__date__range=[date_from, date_to],
        status__in=['confirmed', 'active', 'completed']
    )
    
    expenses_qs = Expense.objects.filter(
        date__range=[date_from, date_to]
    )
    
    maintenance_qs = MaintenanceRecord.objects.filter(
        date_scheduled__range=[date_from, date_to]
    )
    
    # Financial Summary Calculations
    rental_totals = rentals_qs.aggregate(
        total_revenue=Sum('total_amount'),
        total_commission=Sum('commission_amount'),
        avg_daily_rate=Avg('daily_rate')
    )
    
    expense_totals = expenses_qs.aggregate(
        total_expenses=Sum('amount')
    )
    
    maintenance_totals = maintenance_qs.filter(
        status='completed'
    ).aggregate(
        total_maintenance=Sum('total_cost')
    )
    
    # Calculate financial summary
    total_revenue = rental_totals['total_revenue'] or 0
    total_commission = rental_totals['total_commission'] or 0
    total_expenses = (expense_totals['total_expenses'] or 0) + (maintenance_totals['total_maintenance'] or 0)
    net_profit = total_revenue - total_expenses
    
    financial_summary = {
        'total_revenue': total_revenue,
        'total_commission': total_commission,
        'total_expenses': total_expenses,
        'net_profit': net_profit
    }
    
    # Rental Statistics
    rental_stats_data = rentals_qs.aggregate(
        total_rentals=Count('id'),
        active_rentals=Count('id', filter=Q(status='active')),
        avg_rental_days=Avg('number_of_days')
    )
    
    # Calculate overdue rentals
    overdue_rentals = rentals_qs.filter(
        status='active',
        end_date__lt=today
    ).count()
    
    # Calculate utilization rate
    total_vehicles = Vehicle.objects.filter(status__in=['available', 'rented']).count()
    rented_vehicles = Vehicle.objects.filter(status='rented').count()
    utilization_rate = (rented_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0
    
    rental_stats = {
        'total_rentals': rental_stats_data['total_rentals'] or 0,
        'active_rentals': rental_stats_data['active_rentals'] or 0,
        'avg_rental_days': rental_stats_data['avg_rental_days'] or 0,
        'overdue_rentals': overdue_rentals,
        'utilization_rate': round(utilization_rate, 1)
    }
    
    # Top Performing Vehicles
    top_vehicles = Vehicle.objects.filter(
        rentals__start_date__date__range=[date_from, date_to]
    ).annotate(
        rental_count=Count('rentals', filter=Q(rentals__status__in=['confirmed', 'active', 'completed'])),
        total_revenue=Sum('rentals__total_amount', filter=Q(rentals__status__in=['confirmed', 'active', 'completed'])),
        avg_daily_rate=Avg('rentals__daily_rate', filter=Q(rentals__status__in=['confirmed', 'active', 'completed']))
    ).annotate(
        # Calculate utilization as percentage of days rented vs total days in period
        utilization=F('rental_count') * 100 / ((date_to - date_from).days + 1)
    ).order_by('-total_revenue')[:10]
    
    # Top Customers
    top_customers = Customer.objects.filter(
        rentals__start_date__date__range=[date_from, date_to]
    ).annotate(
        rental_count=Count('rentals', filter=Q(rentals__status__in=['confirmed', 'active', 'completed'])),
        total_spent=Sum('rentals__total_amount', filter=Q(rentals__status__in=['confirmed', 'active', 'completed'])),
        avg_days=Avg('rentals__number_of_days', filter=Q(rentals__status__in=['confirmed', 'active', 'completed']))
    ).order_by('-total_spent')[:10]
    
    # Convert avg_days to numeric for top customers
    for customer in top_customers:
        if customer.avg_days:
            customer.avg_days = float(customer.avg_days)
        else:
            customer.avg_days = 0
    
    # Expense Breakdown by Category - Show all categories with expenses in date range
    expense_breakdown = list(ExpenseCategory.objects.annotate(
        total_amount=Sum('expenses__amount', filter=Q(expenses__date__range=[date_from, date_to]))
    ).exclude(total_amount__isnull=True).exclude(total_amount=0).order_by('-total_amount')[:10])
    
    # Calculate percentages for expense breakdown
    total_expense_amount = sum(exp.total_amount for exp in expense_breakdown) if expense_breakdown else 0
    for expense in expense_breakdown:
        expense.percentage = (expense.total_amount / total_expense_amount * 100) if total_expense_amount > 0 else 0
    
    # Monthly Revenue Trend (last 12 months) - Fixed logic
    monthly_revenue = []
    for i in range(11, -1, -1):  # Count backwards from 11 to 0
        month_date = today.replace(day=1) - timedelta(days=30 * i)
        month_start = month_date.replace(day=1)
        # Calculate proper month end
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
        
        month_data = Rental.objects.filter(
            start_date__date__range=[month_start, month_end],
            status__in=['confirmed', 'active', 'completed']
        ).aggregate(
            revenue=Sum('total_amount'),
            commission=Sum('commission_amount')
        )
        
        monthly_revenue.append({
            'month': month_start.strftime('%b %Y'),
            'revenue': float(month_data['revenue'] or 0),
            'commission': float(month_data['commission'] or 0)
        })
    
    # Prepare context
    context = {
        'filters': {
            'date_from': date_from.strftime('%Y-%m-%d') if date_from else '',
            'date_to': date_to.strftime('%Y-%m-%d') if date_to else '',
            'period': period or ''
        },
        'financial_summary': financial_summary,
        'rental_stats': rental_stats,
        'top_vehicles': top_vehicles,
        'top_customers': top_customers,
        'expense_breakdown': expense_breakdown,
        'monthly_revenue': monthly_revenue
    }
    
    # Debug the data being passed
    import json
    print(f"Monthly revenue data: {json.dumps(monthly_revenue, indent=2)}")
    print(f"Expense breakdown count: {len(expense_breakdown)}")
    if expense_breakdown:
        print(f"First expense: {expense_breakdown[0].name} - €{expense_breakdown[0].total_amount} - {expense_breakdown[0].percentage}%")
    
    return render(request, 'vehicle_rental/reports_dashboard.html', context)


@login_required
def revenue_report(request):
    """Revenue report with charts and analytics"""
    
    # Date range filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Revenue data
    rentals = Rental.objects.filter(
        start_date__date__range=[start_date, end_date],
        status__in=['confirmed', 'active', 'completed']
    )
    
    total_revenue = rentals.aggregate(total=Sum('total_amount'))['total'] or 0
    total_commission = rentals.aggregate(total=Sum('commission_amount'))['total'] or 0
    total_rentals = rentals.count()
    average_rental_value = rentals.aggregate(avg=Avg('total_amount'))['avg'] or 0
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_commission': total_commission,
        'total_rentals': total_rentals,
        'average_rental_value': average_rental_value,
        'rentals': rentals.select_related('customer', 'vehicle')[:50],
    }
    
    return render(request, 'vehicle_rental/revenue_report.html', context)


@login_required
def vehicle_utilization_report(request):
    """Vehicle utilization report"""
    
    vehicles = Vehicle.objects.filter(is_active=True).select_related('brand')
    
    # Calculate utilization for each vehicle
    vehicle_data = []
    for vehicle in vehicles:
        total_days = 30  # Last 30 days
        rental_days = vehicle.rentals.filter(
            start_date__gte=timezone.now() - timedelta(days=30),
            status__in=['confirmed', 'active', 'completed']
        ).aggregate(
            total=Sum('number_of_days')
        )['total'] or 0
        
        utilization = (rental_days / total_days) * 100 if total_days > 0 else 0
        
        vehicle_data.append({
            'vehicle': vehicle,
            'rental_days': rental_days,
            'utilization': round(utilization, 2),
            'revenue': vehicle.rentals.filter(
                start_date__gte=timezone.now() - timedelta(days=30)
            ).aggregate(total=Sum('total_amount'))['total'] or 0
        })
    
    # Sort by utilization
    vehicle_data.sort(key=lambda x: x['utilization'], reverse=True)
    
    context = {
        'vehicle_data': vehicle_data,
    }
    
    return render(request, 'vehicle_rental/vehicle_utilization_report.html', context)


# AJAX Views
@login_required
def check_vehicle_availability(request):
    """Check vehicle availability for given date range"""
    
    vehicle_id = request.GET.get('vehicle_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not all([vehicle_id, start_date, end_date]):
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Use the new date-based availability check
        is_available = vehicle.is_available_for_dates(start_date, end_date)
        
        return JsonResponse({
            'available': is_available,
            'vehicle_status': vehicle.status,
            'message': 'Vehicle is available' if is_available else 'Vehicle is not available for selected dates'
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({'error': 'Vehicle not found'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)


@login_required
def calculate_rental_pricing(request):
    """Calculate rental pricing for given vehicle and date range"""
    
    vehicle_id = request.GET.get('vehicle_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not all([vehicle_id, start_date, end_date]):
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Calculate number of days
        delta = end_date - start_date
        number_of_days = max(1, delta.days)
        
        # Calculate pricing
        daily_rate = vehicle.daily_rate
        subtotal = daily_rate * number_of_days
        commission_percent = 10  # Default commission
        commission_amount = (subtotal * commission_percent) / 100
        insurance_fee = 50  # Default insurance fee
        security_deposit = daily_rate * 2  # 2 days as security deposit
        
        # Commission reduces the total amount for customer
        total_amount = subtotal - commission_amount + insurance_fee
        
        return JsonResponse({
            'number_of_days': number_of_days,
            'daily_rate': float(daily_rate),
            'subtotal': float(subtotal),
            'commission_percent': commission_percent,
            'commission_amount': float(commission_amount),
            'insurance_fee': float(insurance_fee),
            'security_deposit': float(security_deposit),
            'total_amount': float(total_amount),
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({'error': 'Vehicle not found'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)


# DRF ViewSets for API
class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.filter(is_active=True).select_related('brand')
    serializer_class = VehicleSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new vehicle with multiple photos"""
        # Create the vehicle first
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vehicle = serializer.save()
        
        # Handle multiple photo uploads
        self._handle_photo_uploads(request, vehicle)
        
        # Return the created vehicle with photos
        headers = self.get_success_headers(serializer.data)
        vehicle_serializer = self.get_serializer(vehicle)
        return Response(vehicle_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """Update vehicle with multiple photos"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Update the vehicle
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        vehicle = serializer.save()
        
        # Handle multiple photo uploads
        self._handle_photo_uploads(request, vehicle)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
            
        # Return the updated vehicle with photos
        vehicle_serializer = self.get_serializer(vehicle)
        return Response(vehicle_serializer.data)
    
    def _handle_photo_uploads(self, request, vehicle):
        """Handle multiple photo uploads for a vehicle"""
        # Get multiple files from the request
        uploaded_files = request.FILES.getlist('additional_photos')
        if not uploaded_files:
            # Also check for 'photos' or 'images' field names
            uploaded_files = request.FILES.getlist('photos') or request.FILES.getlist('images')
        
        created_photos = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            # Get photo metadata for each file
            photo_data = {
                'vehicle': vehicle.id,
                'image': uploaded_file,
                'photo_type': request.data.get(f'photo_type_{i}', request.data.get('photo_type', 'other')),
                'title': request.data.get(f'title_{i}', request.data.get('title', f'Photo {i+1}')),
                'description': request.data.get(f'description_{i}', request.data.get('description', '')),
                'is_primary': request.data.get(f'is_primary_{i}', 'false').lower() == 'true' if i == 0 else False,
            }
            
            # Create photo using the VehiclePhotoSerializer
            photo_serializer = VehiclePhotoSerializer(data=photo_data, context={'request': request})
            if photo_serializer.is_valid():
                photo = photo_serializer.save()
                created_photos.append(photo)
        
        return created_photos
    
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Check vehicle availability"""
        vehicle = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response({'error': 'start_date and end_date are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Implementation for availability check
        return Response({'available': vehicle.is_available})

    @action(detail=True, methods=['get'])
    def evaluations(self, request, pk=None):
        """Get all evaluations for a specific vehicle"""
        vehicle = self.get_object()
        
        # Get all evaluations for this vehicle through rentals
        evaluations = RentalEvaluation.objects.filter(
            rental__vehicle=vehicle
        ).select_related(
            'rental__customer', 
            'rental__vehicle__brand'
        ).order_by('-created_at')
        
        # Apply additional filters if provided
        min_rating = request.query_params.get('min_rating')
        if min_rating:
            try:
                min_rating = int(min_rating)
                evaluations = evaluations.filter(overall_rating__gte=min_rating)
            except ValueError:
                return Response({
                    'error': 'min_rating must be an integer between 1 and 5'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        would_recommend = request.query_params.get('would_recommend')
        if would_recommend is not None:
            evaluations = evaluations.filter(
                would_recommend=would_recommend.lower() == 'true'
            )
        
        had_issues = request.query_params.get('had_issues')
        if had_issues is not None:
            evaluations = evaluations.filter(
                had_issues=had_issues.lower() == 'true'
            )
        
        # Pagination
        page_size = int(request.query_params.get('page_size', 20))
        page_number = int(request.query_params.get('page', 1))
        
        from django.core.paginator import Paginator
        paginator = Paginator(evaluations, page_size)
        page_obj = paginator.get_page(page_number)
        
        # Serialize evaluations
        serializer = RentalEvaluationSerializer(page_obj, many=True)
        
        # Calculate statistics for this vehicle
        total_evaluations = evaluations.count()
        stats = {}
        
        if total_evaluations > 0:
            from django.db.models import Avg
            
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
        
        return Response({
            'vehicle_info': {
                'id': vehicle.id,
                'registration_number': vehicle.registration_number,
                'brand': vehicle.brand.name,
                'model': vehicle.model,
                'year': vehicle.year
            },
            'statistics': stats,
            'evaluations': {
                'count': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'results': serializer.data
            }
        })

    @action(detail=True, methods=['get', 'post'])
    def photos(self, request, pk=None):
        """Manage photos for a specific vehicle"""
        vehicle = self.get_object()
        
        if request.method == 'GET':
            # Get all photos for this vehicle
            photos = VehiclePhoto.objects.filter(vehicle=vehicle).order_by('-is_primary', 'photo_type', '-uploaded_at')
            
            # Group photos by type
            photos_by_type = {}
            primary_photo = None
            
            for photo in photos:
                if photo.is_primary:
                    primary_photo = VehiclePhotoSerializer(photo, context={'request': request}).data
                
                photo_type = photo.photo_type
                if photo_type not in photos_by_type:
                    photos_by_type[photo_type] = []
                photos_by_type[photo_type].append(VehiclePhotoSerializer(photo, context={'request': request}).data)
            
            return Response({
                'vehicle_info': {
                    'id': vehicle.id,
                    'registration_number': vehicle.registration_number,
                    'brand': vehicle.brand.name,
                    'model': vehicle.model,
                    'year': vehicle.year
                },
                'primary_photo': primary_photo,
                'photos_by_type': photos_by_type,
                'total_photos': photos.count(),
                'available_types': [{'value': choice[0], 'label': choice[1]} for choice in VehiclePhoto.PHOTO_TYPE_CHOICES]
            })
        
        elif request.method == 'POST':
            # Upload new photo(s) for this vehicle
            uploaded_files = request.FILES.getlist('images')
            if not uploaded_files:
                # Single file upload
                photo_data = request.data.copy()
                photo_data['vehicle'] = vehicle.id
                
                serializer = VehiclePhotoSerializer(data=photo_data, context={'request': request})
                if serializer.is_valid():
                    photo = serializer.save(uploaded_by=request.user if request.user.is_authenticated else None)
                    return Response({
                        'message': 'Photo uploaded successfully',
                        'photo': VehiclePhotoSerializer(photo, context={'request': request}).data
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Multiple file upload
                created_photos = []
                errors = []
                
                for i, uploaded_file in enumerate(uploaded_files):
                    photo_data = {
                        'vehicle': vehicle.id,
                        'image': uploaded_file,
                        'photo_type': request.data.get(f'photo_type_{i}', request.data.get('photo_type', 'other')),
                        'title': request.data.get(f'title_{i}', request.data.get('title', '')),
                        'description': request.data.get(f'description_{i}', request.data.get('description', '')),
                        'is_primary': request.data.get(f'is_primary_{i}', request.data.get('is_primary', 'false')).lower() == 'true',
                    }
                    
                    serializer = VehiclePhotoSerializer(data=photo_data, context={'request': request})
                    if serializer.is_valid():
                        photo = serializer.save(uploaded_by=request.user if request.user.is_authenticated else None)
                        created_photos.append(VehiclePhotoSerializer(photo, context={'request': request}).data)
                    else:
                        errors.append({'file_index': i, 'filename': uploaded_file.name, 'errors': serializer.errors})
                
                return Response({
                    'message': f'Successfully uploaded {len(created_photos)} photos',
                    'created_photos': created_photos,
                    'errors': errors,
                    'total_uploaded': len(created_photos),
                    'total_errors': len(errors)
                }, status=status.HTTP_201_CREATED if created_photos else status.HTTP_400_BAD_REQUEST)


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class VehicleBrandViewSet(viewsets.ModelViewSet):
    """ViewSet for managing vehicle brands"""
    queryset = VehicleBrand.objects.all().order_by('name')
    serializer_class = VehicleBrandSerializer
    
    def get_queryset(self):
        """Return only brands that have associated vehicles"""
        return VehicleBrand.objects.filter(vehicles__isnull=False).distinct().order_by('name')


class DeliveryLocationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing delivery/return locations"""
    queryset = DeliveryLocation.objects.filter(is_active=True).order_by('name')
    serializer_class = DeliveryLocationSerializer
    permission_classes = [AllowAny]  # No authentication required for location access
    
    def get_queryset(self):
        queryset = super().get_queryset()
        location_type = self.request.query_params.get('location_type', None)
        
        if location_type in ['pickup', 'return', 'both']:
            if location_type == 'pickup':
                queryset = queryset.filter(location_type__in=['pickup', 'both'])
            elif location_type == 'return':
                queryset = queryset.filter(location_type__in=['return', 'both'])
            else:
                queryset = queryset.filter(location_type=location_type)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def defaults(self, request):
        """Get default pickup and return locations"""
        pickup_default = self.get_queryset().filter(
            default_pickup=True,
            location_type__in=['pickup', 'both']
        ).first()
        return_default = self.get_queryset().filter(
            default_return=True,
            location_type__in=['return', 'both']  
        ).first()
        
        return Response({
            'pickup_default': DeliveryLocationSerializer(pickup_default).data if pickup_default else None,
            'return_default': DeliveryLocationSerializer(return_default).data if return_default else None,
        })
    
    def perform_create(self, serializer):
        # Only set created_by if user is authenticated
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    def list(self, request, *args, **kwargs):
        """List all vehicle brands with optional filtering and stats"""
        queryset = self.get_queryset()
        
        # Optional filtering by name
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        # Optional filtering by country
        country = request.query_params.get('country', None)
        if country:
            queryset = queryset.filter(country_of_origin__icontains=country)
        
        # Add vehicle count if requested
        include_stats = request.query_params.get('include_stats', 'false').lower() == 'true'
        
        if include_stats:
            from django.db.models import Count
            queryset = queryset.annotate(
                vehicle_count=Count('vehicles', filter=Q(vehicles__is_active=True)),
                active_vehicle_count=Count('vehicles', filter=Q(vehicles__is_active=True, vehicles__status='available'))
            )
        
        serializer = self.get_serializer(queryset, many=True)
        
        # Add stats to serialized data if requested
        if include_stats:
            data = []
            for i, brand in enumerate(queryset):
                brand_data = serializer.data[i].copy()
                brand_data['vehicle_count'] = brand.vehicle_count
                brand_data['active_vehicle_count'] = brand.active_vehicle_count
                data.append(brand_data)
            return Response(data)
        else:
            return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def vehicles(self, request, pk=None):
        """Get all vehicles for a specific brand"""
        brand = self.get_object()
        vehicles = Vehicle.objects.filter(brand=brand, is_active=True).select_related('brand')
        
        # Optional status filtering
        status_filter = request.query_params.get('status')
        if status_filter:
            vehicles = vehicles.filter(status=status_filter)
        
        from .serializers import VehicleSerializer
        serializer = VehicleSerializer(vehicles, many=True, context={'request': request})
        
        return Response({
            'brand': VehicleBrandSerializer(brand).data,
            'vehicles': serializer.data,
            'total_vehicles': vehicles.count()
        })


class RentalViewSet(viewsets.ModelViewSet):
    queryset = Rental.objects.select_related('customer', 'vehicle')
    serializer_class = RentalSerializer
    
    def perform_create(self, serializer):
        """Send booking notification after creating rental via API"""
        rental = serializer.save()
        try:
            _send_rental_booking_email(rental, self.request)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send booking email for rental {rental.id}: {str(e)}")
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a pending rental"""
        rental = self.get_object()
        
        if rental.status == 'pending':
            rental.status = 'confirmed'
            rental.save()
            
            # Send confirmation email
            try:
                _send_rental_confirmation_email(rental)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send confirmation email for rental {rental.id}: {str(e)}")
            
            return Response({
                'status': 'success',
                'message': f'Rental #{rental.id} confirmed successfully',
                'rental_status': rental.status
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'message': 'Only pending rentals can be confirmed',
                'current_status': rental.status
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a rental"""
        rental = self.get_object()
        
        if rental.status in ['pending', 'confirmed']:
            rental.status = 'cancelled'
            rental.save()
            
            # Send cancellation notification email
            try:
                _send_rental_cancellation_email(rental)
            except Exception as e:
                logger.error(f"Failed to send cancellation email for rental {rental.id}: {str(e)}")
            
            return Response({
                'status': 'success',
                'message': f'Rental #{rental.id} cancelled successfully',
                'rental_status': rental.status
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'message': 'Only pending or confirmed rentals can be cancelled',
                'current_status': rental.status
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def return_rental(self, request, pk=None):
        """Process rental return (devolution)"""
        rental = self.get_object()
        
        if rental.status in ['confirmed', 'active']:
            # Get return details from request data
            actual_return_date = request.data.get('actual_return_date')
            odometer_end = request.data.get('odometer_end')
            fuel_level_end = request.data.get('fuel_level_end')
            damage_description = request.data.get('damage_description', '')
            damage_fee = request.data.get('damage_fee', 0)
            late_return_fee = request.data.get('late_return_fee', 0)
            additional_charges = request.data.get('additional_charges', 0)
            
            # Validate required fields
            if not actual_return_date:
                return Response({
                    'status': 'error',
                    'message': 'actual_return_date is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse date
            from datetime import datetime
            try:
                if isinstance(actual_return_date, str):
                    actual_return_date = datetime.strptime(actual_return_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update rental
            rental.actual_return_date = actual_return_date
            rental.status = 'completed'
            
            if odometer_end:
                rental.odometer_end = odometer_end
            if fuel_level_end:
                rental.fuel_level_end = fuel_level_end
            if damage_description:
                rental.damage_description = damage_description
            if damage_fee:
                rental.damage_fee = damage_fee
            if late_return_fee:
                rental.late_return_fee = late_return_fee
            if additional_charges:
                rental.additional_charges = additional_charges
            
            rental.save()
            
            # Send return email with evaluation link
            try:
                _send_rental_return_email(rental, request)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send return email for rental {rental.id}: {str(e)}")
            
            return Response({
                'status': 'success',
                'message': f'Rental #{rental.id} returned successfully',
                'rental_status': rental.status,
                'actual_return_date': rental.actual_return_date,
                'total_amount': rental.total_amount
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'message': 'Only confirmed or active rentals can be returned',
                'current_status': rental.status
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def create_evaluation(self, request, pk=None):
        """Create evaluation for a completed rental"""
        rental = self.get_object()
        
        # Check if rental is completed
        if rental.status != 'completed':
            return Response({
                'status': 'error',
                'message': 'Only completed rentals can be evaluated'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if evaluation already exists
        if hasattr(rental, 'evaluation'):
            return Response({
                'status': 'error',
                'message': 'This rental has already been evaluated'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create evaluation
        evaluation_data = request.data.copy()
        evaluation_data['rental'] = rental.id
        
        serializer = RentalEvaluationSerializer(data=evaluation_data)
        if serializer.is_valid():
            evaluation = serializer.save()
            return Response({
                'status': 'success',
                'message': 'Evaluation created successfully',
                'evaluation': RentalEvaluationSerializer(evaluation).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'status': 'error',
                'message': 'Invalid evaluation data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def can_evaluate(self, request, pk=None):
        """Check if a rental can be evaluated"""
        rental = self.get_object()
        
        can_evaluate = (
            rental.status == 'completed' and 
            not hasattr(rental, 'evaluation')
        )
        
        return Response({
            'can_evaluate': can_evaluate,
            'rental_status': rental.status,
            'has_evaluation': hasattr(rental, 'evaluation'),
            'evaluation_id': rental.evaluation.id if hasattr(rental, 'evaluation') else None
        })


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.select_related('vehicle', 'category')
    serializer_class = ExpenseSerializer


class MaintenanceRecordViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRecord.objects.select_related('vehicle')
    serializer_class = MaintenanceRecordSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def start(self, request, pk=None):
        """Start a maintenance record - change status to in_progress"""
        maintenance = self.get_object()
        
        if maintenance.status == 'in_progress':
            return Response(
                {'error': 'Manutenção já está em progresso'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if maintenance.status == 'completed':
            return Response(
                {'error': 'Manutenção já foi concluída'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if maintenance.status == 'cancelled':
            return Response(
                {'error': 'Manutenção foi cancelada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status to in_progress
        maintenance.status = 'in_progress'
        maintenance.save()
        
        # Update vehicle status to maintenance if not already
        if maintenance.vehicle.status != 'maintenance':
            maintenance.vehicle.status = 'maintenance'
            maintenance.vehicle.save()
        
        serializer = self.get_serializer(maintenance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def complete(self, request, pk=None):
        """Complete a maintenance record"""
        maintenance = self.get_object()
        
        if maintenance.status == 'completed':
            return Response(
                {'error': 'Manutenção já foi concluída'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if maintenance.status == 'cancelled':
            return Response(
                {'error': 'Manutenção foi cancelada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update maintenance record
        maintenance.status = 'completed'
        
        # Update date_completed if provided
        completed_date = request.data.get('completed_date')
        if completed_date:
            from datetime import datetime
            try:
                # Parse ISO format datetime
                maintenance.date_completed = datetime.fromisoformat(completed_date.replace('Z', '+00:00')).date()
            except (ValueError, AttributeError):
                maintenance.date_completed = timezone.now().date()
        else:
            maintenance.date_completed = timezone.now().date()
        
        # Update costs if provided
        labor_cost = request.data.get('labor_cost')
        if labor_cost:
            maintenance.labor_cost = Decimal(labor_cost)
        
        parts_cost = request.data.get('parts_cost')
        if parts_cost:
            maintenance.parts_cost = Decimal(parts_cost)
        
        other_cost = request.data.get('other_cost')
        if other_cost:
            maintenance.other_costs = Decimal(other_cost)
        
        # Recalculate total cost
        maintenance.labor_cost = maintenance.labor_cost or 0
        maintenance.parts_cost = maintenance.parts_cost or 0
        maintenance.other_costs = maintenance.other_costs or 0
        maintenance.total_cost = maintenance.labor_cost + maintenance.parts_cost + maintenance.other_costs
        
        # Update warranty if provided
        warranty_period_months = request.data.get('warranty_period_months')
        if warranty_period_months:
            # Calculate warranty end date (approximate: 30 days per month)
            days = int(warranty_period_months) * 30
            maintenance.warranty_until = maintenance.date_completed + timedelta(days=days)
        
        # Update next service date if provided
        next_service_date = request.data.get('next_service_date')
        if next_service_date:
            maintenance.next_service_date = next_service_date
        
        maintenance.save()
        
        # Check if vehicle should return to available status
        # Only if there are no other active maintenance records
        active_maintenance = MaintenanceRecord.objects.filter(
            vehicle=maintenance.vehicle,
            status__in=['scheduled', 'in_progress']
        ).exclude(pk=maintenance.pk).exists()
        
        if not active_maintenance:
            # Check if vehicle is in an active rental
            from datetime import date
            active_rental = Rental.objects.filter(
                vehicle=maintenance.vehicle,
                status='active',
                end_date__gte=date.today()
            ).exists()
            
            if not active_rental:
                maintenance.vehicle.status = 'available'
                maintenance.vehicle.save()
        
        serializer = self.get_serializer(maintenance)
        return Response(serializer.data)


class RentalEvaluationViewSet(viewsets.ModelViewSet):
    queryset = RentalEvaluation.objects.select_related('rental__customer', 'rental__vehicle__brand')
    serializer_class = RentalEvaluationSerializer
    
    def get_queryset(self):
        """Filter evaluations based on query parameters"""
        queryset = self.queryset
        
        # Filter by rental ID
        rental_id = self.request.query_params.get('rental_id')
        if rental_id:
            queryset = queryset.filter(rental_id=rental_id)
        
        # Filter by customer
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(rental__customer_id=customer_id)
        
        # Filter by vehicle
        vehicle_id = self.request.query_params.get('vehicle_id')
        if vehicle_id:
            queryset = queryset.filter(rental__vehicle_id=vehicle_id)
        
        # Filter by rating
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(overall_rating__gte=min_rating)
        
        # Filter by recommendation
        would_recommend = self.request.query_params.get('would_recommend')
        if would_recommend is not None:
            queryset = queryset.filter(would_recommend=would_recommend.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get evaluation statistics"""
        evaluations = self.get_queryset()
        
        if not evaluations.exists():
            return Response({
                'total_evaluations': 0,
                'average_overall_rating': 0,
                'average_vehicle_condition': 0,
                'average_service_quality': 0,
                'average_value_for_money': 0,
                'recommendation_percentage': 0,
                'issues_percentage': 0
            })
        
        total = evaluations.count()
        avg_overall = evaluations.aggregate(avg=Avg('overall_rating'))['avg']
        avg_vehicle = evaluations.aggregate(avg=Avg('vehicle_condition_rating'))['avg']
        avg_service = evaluations.aggregate(avg=Avg('service_quality_rating'))['avg']
        avg_value = evaluations.aggregate(avg=Avg('value_for_money_rating'))['avg']
        
        recommendations = evaluations.filter(would_recommend=True).count()
        issues = evaluations.filter(had_issues=True).count()
        
        return Response({
            'total_evaluations': total,
            'average_overall_rating': round(avg_overall, 2) if avg_overall else 0,
            'average_vehicle_condition': round(avg_vehicle, 2) if avg_vehicle else 0,
            'average_service_quality': round(avg_service, 2) if avg_service else 0,
            'average_value_for_money': round(avg_value, 2) if avg_value else 0,
            'recommendation_percentage': round((recommendations / total) * 100, 2),
            'issues_percentage': round((issues / total) * 100, 2)
        })


class VehiclePhotoViewSet(viewsets.ModelViewSet):
    queryset = VehiclePhoto.objects.select_related('vehicle', 'uploaded_by')
    serializer_class = VehiclePhotoSerializer
    
    def get_queryset(self):
        """Filter photos based on query parameters"""
        queryset = self.queryset
        
        # Filter by vehicle ID
        vehicle_id = self.request.query_params.get('vehicle_id')
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)
        
        # Filter by photo type
        photo_type = self.request.query_params.get('photo_type')
        if photo_type:
            queryset = queryset.filter(photo_type=photo_type)
        
        # Filter by primary status
        is_primary = self.request.query_params.get('is_primary')
        if is_primary is not None:
            queryset = queryset.filter(is_primary=is_primary.lower() == 'true')
        
        return queryset.order_by('-is_primary', 'photo_type', '-uploaded_at')
    
    def perform_create(self, serializer):
        """Set the uploaded_by field to the current user"""
        serializer.save(uploaded_by=self.request.user if self.request.user.is_authenticated else None)
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """Upload multiple photos for a vehicle at once"""
        vehicle_id = request.data.get('vehicle_id')
        if not vehicle_id:
            return Response({'error': 'vehicle_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get uploaded files
        uploaded_files = request.FILES.getlist('images')
        if not uploaded_files:
            return Response({'error': 'No images provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        created_photos = []
        errors = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            # Get additional data for each photo
            photo_data = {
                'vehicle': vehicle.id,
                'image': uploaded_file,
                'photo_type': request.data.get(f'photo_type_{i}', 'other'),
                'title': request.data.get(f'title_{i}', ''),
                'description': request.data.get(f'description_{i}', ''),
                'is_primary': request.data.get(f'is_primary_{i}', 'false').lower() == 'true',
            }
            
            serializer = VehiclePhotoSerializer(data=photo_data, context={'request': request})
            if serializer.is_valid():
                photo = serializer.save()
                created_photos.append(serializer.data)
            else:
                errors.append({'file_index': i, 'filename': uploaded_file.name, 'errors': serializer.errors})
        
        return Response({
            'message': f'Successfully uploaded {len(created_photos)} photos',
            'created_photos': created_photos,
            'errors': errors,
            'total_uploaded': len(created_photos),
            'total_errors': len(errors)
        }, status=status.HTTP_201_CREATED if created_photos else status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set this photo as the primary photo for its vehicle"""
        photo = self.get_object()
        
        # Unmark all other primary photos for this vehicle
        VehiclePhoto.objects.filter(vehicle=photo.vehicle, is_primary=True).update(is_primary=False)
        
        # Mark this photo as primary
        photo.is_primary = True
        photo.save()
        
        return Response({
            'message': f'Photo {photo.id} set as primary for vehicle {photo.vehicle.registration_number}',
            'photo': VehiclePhotoSerializer(photo, context={'request': request}).data
        })
    
    @action(detail=False, methods=['get'])
    def by_vehicle(self, request):
        """Get all photos for a specific vehicle with grouping by type"""
        vehicle_id = request.query_params.get('vehicle_id')
        if not vehicle_id:
            return Response({'error': 'vehicle_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)
        
        photos = VehiclePhoto.objects.filter(vehicle=vehicle).order_by('-is_primary', 'photo_type', '-uploaded_at')
        
        # Group photos by type
        photos_by_type = {}
        primary_photo = None
        
        for photo in photos:
            if photo.is_primary:
                primary_photo = VehiclePhotoSerializer(photo, context={'request': request}).data
            
            photo_type = photo.photo_type
            if photo_type not in photos_by_type:
                photos_by_type[photo_type] = []
            photos_by_type[photo_type].append(VehiclePhotoSerializer(photo, context={'request': request}).data)
        
        return Response({
            'vehicle_info': {
                'id': vehicle.id,
                'registration_number': vehicle.registration_number,
                'brand': vehicle.brand.name,
                'model': vehicle.model,
                'year': vehicle.year
            },
            'primary_photo': primary_photo,
            'photos_by_type': photos_by_type,
            'total_photos': photos.count(),
            'available_types': [{'value': choice[0], 'label': choice[1]} for choice in VehiclePhoto.PHOTO_TYPE_CHOICES]
        })


# API endpoint for creating vehicle brands from the form
@login_required
def api_create_brand(request):
    """API endpoint to create a new vehicle brand"""
    if request.method == 'POST':
        try:
            brand_name = request.POST.get('name', '').strip()
            
            if not brand_name:
                return JsonResponse({'error': 'Brand name is required'}, status=400)
            
            # Check if brand already exists
            if VehicleBrand.objects.filter(name__iexact=brand_name).exists():
                return JsonResponse({'error': 'Brand already exists'}, status=400)
            
            # Create new brand
            brand = VehicleBrand.objects.create(name=brand_name)
            
            return JsonResponse({
                'id': brand.id,
                'name': brand.name,
                'success': True,
                'brand': {'id': brand.id, 'name': brand.name}
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def rental_invoice(request, pk):
    """Generate and display rental invoice"""
    rental = get_object_or_404(
        Rental.objects.select_related('customer', 'vehicle', 'vehicle__brand'),
        pk=pk
    )
    
    # Calculate rental duration
    try:
        rental_duration = rental.get_rental_duration  # It's a property, not a method
    except (AttributeError, TypeError):
        # Fallback calculation if property doesn't exist or fails
        if rental.actual_return_date:
            rental_duration = (rental.actual_return_date.date() - rental.start_date.date()).days + 1
        else:
            rental_duration = (rental.end_date.date() - rental.start_date.date()).days + 1
    
    # Ensure rental_duration is not None
    if rental_duration is None or rental_duration <= 0:
        rental_duration = 1
    
    # Calculate invoice details
    invoice_data = {
        'rental': rental,
        'invoice_number': f'INV-{rental.id:05d}',
        'invoice_date': timezone.now().date(),
        'due_date': timezone.now().date() + timedelta(days=30),
        'subtotal': rental.subtotal or (rental.daily_rate * rental_duration),
        'total_fees': (rental.late_return_fee or 0) + (rental.damage_fee or 0),
        'total_amount': rental.total_amount,
        'rental_duration': rental_duration,
    }
    
    # Get related expenses if any
    expenses = rental.expenses.select_related('category').all()
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    invoice_data.update({
        'expenses': expenses,
        'total_expenses': total_expenses,
        'grand_total': rental.total_amount + total_expenses
    })
    
    # Check if it's a PDF request
    if request.GET.get('format') == 'pdf':
        return generate_invoice_pdf(request, invoice_data)
    
    context = {
        'invoice_data': invoice_data,
        'company_info': {
            'name': 'Universal Rent a Car',
            'address': 'Achada Santo António',
            'city': 'Praia, Cabo Verde',
            'phone': '(+238) 978 13 04 / (+238) 347 6581',
            'email': 'universal.r.car@gmail.com',
            'vat_number': ''
        }
    }
    
    return render(request, 'vehicle_rental/rental_invoice.html', context)


def generate_invoice_pdf(request, invoice_data):
    """Generate PDF invoice using ReportLab"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import cm
        from io import BytesIO
        import locale
        
        # Set up response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="fatura_{invoice_data["invoice_number"]}.pdf"'
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        
        # Styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', parent=styles['Normal'], alignment=1))
        styles.add(ParagraphStyle(name='Right', parent=styles['Normal'], alignment=2))
        styles.add(ParagraphStyle(name='CompanyTitle', parent=styles['Title'], fontSize=24, textColor=colors.blue))
        
        # Story - content to be added to PDF
        story = []
        
        # Company header
        story.append(Paragraph("BoZ Rental Services", styles['CompanyTitle']))
        story.append(Paragraph("Rua Principal, 123<br/>Lisboa, Portugal<br/>Tel: +351 123 456 789<br/>Email: info@bozrental.pt<br/>NIF: PT123456789", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Invoice title and details
        story.append(Paragraph(f"<b>FATURA {invoice_data['invoice_number']}</b>", styles['Title']))
        story.append(Spacer(1, 20))
        
        # Invoice info table
        invoice_info_data = [
            ['Data da Fatura:', invoice_data['invoice_date'].strftime('%d/%m/%Y')],
            ['Data de Vencimento:', invoice_data['due_date'].strftime('%d/%m/%Y')],
            ['Aluguer ID:', f"#{invoice_data['rental'].id}"],
        ]
        
        invoice_info_table = Table(invoice_info_data, colWidths=[4*cm, 6*cm])
        invoice_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(invoice_info_table)
        story.append(Spacer(1, 20))
        
        # Customer info
        rental = invoice_data['rental']
        story.append(Paragraph("<b>Cliente:</b>", styles['Heading3']))
        customer_text = f"{rental.customer.first_name} {rental.customer.last_name}<br/>"
        if rental.customer.email:
            customer_text += f"Email: {rental.customer.email}<br/>"
        if rental.customer.phone_number:
            customer_text += f"Telefone: {rental.customer.phone_number}<br/>"
        story.append(Paragraph(customer_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Vehicle info
        story.append(Paragraph("<b>Veículo:</b>", styles['Heading3']))
        vehicle_text = f"{rental.vehicle.brand.name} {rental.vehicle.model}<br/>"
        vehicle_text += f"Matrícula: {rental.vehicle.registration_number}<br/>"
        vehicle_text += f"Ano: {rental.vehicle.year}<br/>"
        story.append(Paragraph(vehicle_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Rental period
        story.append(Paragraph("<b>Período de Aluguer:</b>", styles['Heading3']))
        period_text = f"Início: {rental.start_date.strftime('%d/%m/%Y %H:%M')}<br/>"
        period_text += f"Fim: {rental.end_date.strftime('%d/%m/%Y %H:%M')}<br/>"
        if rental.actual_return_date:
            period_text += f"Devolução Real: {rental.actual_return_date.strftime('%d/%m/%Y %H:%M')}<br/>"
        period_text += f"Duração: {invoice_data['rental_duration']} dias"
        story.append(Paragraph(period_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Billing details table
        story.append(Paragraph("<b>Detalhes da Fatura:</b>", styles['Heading3']))
        
        billing_data = [
            ['Descrição', 'Quantidade', 'Preço Unitário', 'Total'],
            [f'Aluguer de {rental.vehicle.brand.name} {rental.vehicle.model}', 
             f'{invoice_data["rental_duration"]} dias', 
             f'€{rental.daily_rate:.2f}', 
             f'€{invoice_data["subtotal"]:.2f}']
        ]
        
        # Add expenses if any
        if invoice_data.get('expenses') and invoice_data['expenses'].exists():
            for expense in invoice_data['expenses']:
                billing_data.append([
                    f'Despesa: {expense.description}',
                    '1',
                    f'€{expense.amount:.2f}',
                    f'€{expense.amount:.2f}'
                ])
        
        # Add fees if any
        if invoice_data['total_fees'] > 0:
            if rental.late_return_fee and rental.late_return_fee > 0:
                billing_data.append([
                    'Taxa de Atraso',
                    '1',
                    f'€{rental.late_return_fee:.2f}',
                    f'€{rental.late_return_fee:.2f}'
                ])
            if rental.damage_fee and rental.damage_fee > 0:
                billing_data.append([
                    'Taxa de Danos',
                    '1', 
                    f'€{rental.damage_fee:.2f}',
                    f'€{rental.damage_fee:.2f}'
                ])
        
        billing_table = Table(billing_data, colWidths=[8*cm, 2*cm, 3*cm, 3*cm])
        billing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Description column left aligned
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(billing_table)
        story.append(Spacer(1, 20))
        
        # Total section
        total_data = [
            ['Subtotal:', f'€{invoice_data["subtotal"]:.2f}'],
            ['Total de Despesas:', f'€{invoice_data["total_expenses"]:.2f}'],
            ['Total de Taxas:', f'€{invoice_data["total_fees"]:.2f}'],
            ['<b>TOTAL GERAL:</b>', f'<b>€{invoice_data["grand_total"]:.2f}</b>']
        ]
        
        total_table = Table(total_data, colWidths=[8*cm, 4*cm])
        total_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(total_table)
        story.append(Spacer(1, 30))
        
        # Footer
        story.append(Paragraph("Obrigado pelo seu negócio!", styles['Center']))
        story.append(Paragraph("Para questões sobre esta fatura, contacte-nos através do email ou telefone acima.", styles['Center']))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        response.write(pdf_content)
        return response
        
    except ImportError as e:
        messages.error(request, f'PDF generation requires ReportLab. Error: {str(e)}')
        return redirect('vehicle_rental:rental_invoice', pk=invoice_data['rental'].pk)
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('vehicle_rental:rental_invoice', pk=invoice_data['rental'].pk)


# Customer-facing API ViewSets

class CustomerRegistrationViewSet(viewsets.GenericViewSet):
    """ViewSet for customer self-registration"""
    serializer_class = None  # Will be set in get_serializer_class
    permission_classes = []  # Allow unauthenticated access for registration
    
    def get_serializer_class(self):
        from .serializers import CustomerRegistrationSerializer, CustomerDetailSerializer
        if self.action == 'create':
            return CustomerRegistrationSerializer
        return CustomerDetailSerializer
    
    def create(self, request):
        """Register a new customer"""

        print("Received registration data:", request.data)  # Debug statement
        from .serializers import CustomerRegistrationSerializer
        serializer = CustomerRegistrationSerializer(data=request.data)

        print("Serializer created, checking validity...")  # Debug statement
        is_valid = serializer.is_valid()
        print("Serializer valid:", is_valid)  # Debug statement
        
        if not is_valid:
            print("Serializer errors:", serializer.errors)  # Debug statement
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        if serializer.is_valid():
            customer = serializer.save()
            
            # Send welcome email
            try:
                _send_welcome_email(customer, request)
            except Exception as e:
                logger.error(f'Failed to send welcome email for customer #{customer.id}: {str(e)}')
                # Don't prevent registration if email fails
            
            from .serializers import CustomerDetailSerializer
            response_serializer = CustomerDetailSerializer(customer)
            return Response({
                'message': 'Customer registered successfully',
                'customer': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current customer's profile"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            customer = request.user.customer_profile
            from .serializers import CustomerDetailSerializer
            serializer = CustomerDetailSerializer(customer)
            return Response(serializer.data)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        """Update current customer's profile"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            customer = request.user.customer_profile
            from .serializers import CustomerDetailSerializer
            serializer = CustomerDetailSerializer(customer, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Profile updated successfully',
                    'customer': serializer.data
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=status.HTTP_404_NOT_FOUND)


class CustomerRentalViewSet(viewsets.ModelViewSet):
    """ViewSet for customers to manage their rentals"""
    serializer_class = None  # Will be set in get_serializer_class
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        from .serializers import CustomerRentalSerializer, RentalSerializer
        if self.action == 'create':
            return RentalSerializer
        return CustomerRentalSerializer
    
    def get_queryset(self):
        try:
            customer = self.request.user.customer_profile
            return Rental.objects.filter(customer=customer).select_related(
                'vehicle', 'vehicle__brand'
            ).order_by('-created_at')
        except Customer.DoesNotExist:
            return Rental.objects.none()
    
    def create(self, request):
        """Create a new rental for the authenticated customer"""
        try:
            customer = request.user.customer_profile
        except Customer.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Add customer to rental data
        rental_data = request.data.copy()
        rental_data['customer'] = customer.id
        
        from .serializers import RentalSerializer
        serializer = RentalSerializer(data=rental_data, context={'request': request})
        if serializer.is_valid():
            rental = serializer.save()
            
            # Send booking notification email
            try:
                _send_rental_booking_email(rental, request)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send booking email for rental {rental.id}: {str(e)}")
            
            from .serializers import CustomerRentalSerializer
            return Response({
                'message': 'Rental created successfully',
                'rental': CustomerRentalSerializer(rental, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get customer's active rentals"""
        queryset = self.get_queryset().filter(status__in=['pending', 'confirmed', 'active'])
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get customer's completed or cancelled rentals"""
        queryset = self.get_queryset().filter(status__in=['completed', 'cancelled'])
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending or confirmed rental"""
        rental = self.get_object()
        
        if rental.status not in ['pending', 'confirmed']:
            return Response({
                'error': f'Cannot cancel rental with status: {rental.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        rental.status = 'cancelled'
        rental.save()
        
        # Send cancellation notification email
        try:
            _send_rental_cancellation_email(rental)
        except Exception as e:
            logger.error(f"Failed to send cancellation email for rental {rental.id}: {str(e)}")
        
        serializer = self.get_serializer(rental)
        return Response({
            'message': 'Rental cancelled successfully',
            'rental': serializer.data
        })

class CustomerRentalEvaluationViewSet(viewsets.ModelViewSet):
    """ViewSet for customers to create and view rental evaluations"""
    serializer_class = RentalEvaluationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            customer = self.request.user.customer_profile
            return RentalEvaluation.objects.filter(
                rental__customer=customer
            ).select_related('rental', 'rental__vehicle', 'rental__vehicle__brand')
        except Customer.DoesNotExist:
            return RentalEvaluation.objects.none()
    
    def create(self, request):
        """Create a new rental evaluation"""
        try:
            customer = request.user.customer_profile
        except Customer.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Verify the rental belongs to the customer
        rental_id = request.data.get('rental')
        if not rental_id:
            return Response({'error': 'rental field is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            rental = Rental.objects.get(id=rental_id, customer=customer)
        except Rental.DoesNotExist:
            return Response({'error': 'Rental not found or does not belong to you'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if rental is completed
        if rental.status != 'completed':
            return Response({
                'error': 'Only completed rentals can be evaluated'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if evaluation already exists
        if RentalEvaluation.objects.filter(rental=rental).exists():
            return Response({
                'error': 'This rental has already been evaluated'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Evaluation created successfully',
                'evaluation': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for retrieving customer notifications"""
    serializer_class = None  # Will be set in get_serializer_class
    permission_classes = []  # Allow unauthenticated access (customer_id in URL)
    
    def get_serializer_class(self):
        from .serializers import CustomerNotificationSerializer
        return CustomerNotificationSerializer
    
    def get_queryset(self):
        """Return notifications for the specified customer"""
        customer_id = self.kwargs.get('customer_id')
        if customer_id:
            return CustomerNotification.objects.filter(
                customer_id=customer_id
            ).order_by('-created_at')
        return CustomerNotification.objects.none()
    
    def list(self, request, customer_id=None):
        """List all notifications for a customer, ordered by most recent"""
        if not customer_id:
            return Response({
                'error': 'Customer ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'customer_id': customer_id,
            'total_notifications': queryset.count(),
            'notifications': serializer.data
        })


class VehicleAvailabilityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for customers to view available vehicles"""
    serializer_class = None  # Will be set in get_serializer_class
    permission_classes = []  # Public access
    
    def get_serializer_class(self):
        from .serializers import CustomerVehicleSerializer, VehicleSerializer
        # Use simplified serializer for list view, full serializer for detail view
        if self.action == 'list':
            return CustomerVehicleSerializer
        return VehicleSerializer
    
    def get_queryset(self):
        """Return only available, active vehicles"""
        queryset = Vehicle.objects.filter(
            status='available',
            is_active=True
        ).select_related('brand').prefetch_related('additional_photos')
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date and end_date:
            from datetime import datetime
            try:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                
                # Exclude vehicles with overlapping rentals
                overlapping_rentals = Rental.objects.filter(
                    status__in=['pending', 'confirmed', 'active'],
                    start_date__lt=end,
                    end_date__gt=start
                ).values_list('vehicle_id', flat=True)
                
                queryset = queryset.exclude(id__in=overlapping_rentals)
            except (ValueError, TypeError):
                pass  # Invalid date format, ignore filter
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Check specific vehicle availability for a date range"""
        vehicle = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response({
                'error': 'start_date and end_date parameters are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from datetime import datetime
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            # Check for overlapping rentals
            has_conflict = Rental.objects.filter(
                vehicle=vehicle,
                status__in=['pending', 'confirmed', 'active'],
                start_date__lt=end,
                end_date__gt=start
            ).exists()
            
            is_available = not has_conflict and vehicle.status == 'available' and vehicle.is_active
            
            return Response({
                'vehicle_id': vehicle.id,
                'registration_number': vehicle.registration_number,
                'is_available': is_available,
                'start_date': start_date,
                'end_date': end_date
            })
        except (ValueError, TypeError) as e:
            return Response({
                'error': f'Invalid date format: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


# Custom Login API for Customers
@api_view(['POST'])
@permission_classes([AllowAny])
def customer_login(request):
    """
    Custom login endpoint for customers that returns token and customer profile
    
    POST /vehicle-rental/api/customer/login/
    Body: {
        "email": "customer@example.com",
        "password": "password123"
    }
    
    Returns: {
        "token": "abc123...",
        "user": {
            "id": 1,
            "username": "customer@example.com",
            "email": "customer@example.com",
            "is_customer": true
        },
        "customer": {
            "id": 1,
            "first_name": "John",
            "last_name": "Doe",
            ...
        }
    }
    """
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response({
            'error': 'Please provide both email and password'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Authenticate user (username is email)
    user = authenticate(username=email, password=password)
    
    if user is None:
        return Response({
            'error': 'Invalid email or password'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Check if user is a customer
    try:
        customer = Customer.objects.get(user=user)
    except Customer.DoesNotExist:
        return Response({
            'error': 'This account is not a customer account'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check if customer is blacklisted
    if customer.is_blacklisted:
        return Response({
            'error': 'Your account has been suspended. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get or create token
    token, created = Token.objects.get_or_create(user=user)
    
    # Serialize customer data
    from .serializers import CustomerDetailSerializer
    customer_serializer = CustomerDetailSerializer(customer)
    
    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_customer': user.groups.filter(name='customer').exists()
        },
        'customer': customer_serializer.data,
        'message': 'Login successful'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change customer password by customer ID
    
    Required fields: customer_id, current_password, new_password, confirm_password
    
    Example request:
    {
        "customer_id": 1,
        "current_password": "oldpassword123",
        "new_password": "newpassword456", 
        "confirm_password": "newpassword456"
    }
    """
    serializer = ChangePasswordSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    customer = validated_data['customer']
    new_password = validated_data['new_password']
    
    # Change password
    customer.user.set_password(new_password)
    customer.user.save()
    
    return Response({
        'message': 'Password changed successfully',
        'customer_id': customer.id,
        'customer_name': customer.full_name
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """
    Request password reset by sending OTP to email
    
    POST /vehicle-rental/api/customer/request-password-reset/
    Body: {
        "email": "customer@example.com"
    }
    
    Returns: {
        "message": "OTP sent to your email",
        "email": "customer@example.com"
    }
    """
    from django.contrib.auth.models import User
    from django.core.mail import send_mail
    from django.conf import settings
    import random
    import string
    
    email = request.data.get('email')
    
    if not email:
        return Response({
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if customer with this email exists
    try:
        customer = Customer.objects.get(email=email)
    except Customer.DoesNotExist:
        return Response({
            'error': 'Customer with this email does not exist'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Generate a 6-digit OTP
    otp = ''.join(random.choices(string.digits, k=6))
    
    # Save OTP to customer
    customer.otp = otp
    customer.otp_created_at = timezone.now()
    customer.save()
    
    # Send OTP via email
    try:
        from django.template.loader import render_to_string
        from urllib.parse import urlencode
        
        # Get password recovery URL from settings/env
        recovery_base_url = os.environ.get('PASSWORD_RECOVERY_URL', 'http://localhost:8080/universal-rent-a-car/forgot-password-recovery')
        
        # Build recovery URL with email and OTP parameters
        params = urlencode({'email': email, 'otp': otp})
        recovery_url = f"{recovery_base_url}?{params}"
        
        subject = 'Recuperação de Senha - Universal Rent a Car'
        
        # Render HTML template
        context = {
            'customer': customer,
            'otp': otp,
            'recovery_url': recovery_url,
            'company_name': 'Universal Rent a Car',
            'company_email': 'universal.r.car@gmail.com',
            'company_phone1': '(+238) 978 13 04',
            'company_phone2': '(+238) 347 6581',
        }
        
        html_body = render_to_string('vehicle_rental/email/password_recovery.html', context)
        
        # Plain-text fallback
        text_body = f'''
Olá {customer.full_name},

Recebemos um pedido de recuperação de senha para a sua conta.

O seu código de verificação é: {otp}

Ou clique no link abaixo para redefinir a senha directamente:
{recovery_url}

Este código expira em 15 minutos por motivos de segurança.

Se não solicitou esta recuperação de senha, ignore este email.

Atenciosamente,
Universal Rent a Car
        '''
        
        from django.core.mail import EmailMultiAlternatives
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@universalrentacar.com',
            to=[email]
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        
        # Check if we're in development mode (console backend)
        is_console_backend = getattr(settings, 'EMAIL_BACKEND', '') == 'django.core.mail.backends.console.EmailBackend'
        
        return Response({
            'message': 'OTP sent to your email successfully',
            'email': email,
            'dev_mode': is_console_backend,
            'otp': otp if is_console_backend else None  # Only show OTP in dev mode
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # Log the specific error for debugging
        print(f"Email sending failed: {str(e)}")
        
        # Check if it's an email configuration issue
        error_message = str(e).lower()
        if 'authentication failed' in error_message or 'invalid credentials' in error_message:
            detailed_error = 'Email authentication failed. Please check Gmail app password configuration.'
        elif 'connection' in error_message or 'timeout' in error_message:
            detailed_error = 'Email server connection failed. Please check internet connection.'
        elif 'smtp' in error_message:
            detailed_error = 'SMTP configuration error. Please verify email settings.'
        else:
            detailed_error = f'Email sending failed: {str(e)[:100]}'
        
        # For development/testing - return OTP in error response
        is_console_backend = getattr(settings, 'EMAIL_BACKEND', '') == 'django.core.mail.backends.console.EmailBackend'
        
        # Don't clear OTP immediately - keep it for manual use
        return Response({
            'error': detailed_error,
            'email': email,
            'dev_otp': otp if settings.DEBUG else None,  # Only in debug mode
            'suggestion': 'You can temporarily switch to console email backend in settings.py for testing'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Reset password using OTP
    
    POST /vehicle-rental/api/customer/reset-password/
    Body: {
        "email": "customer@example.com",
        "otp": "123456",
        "new_password": "newpassword123",
        "confirm_password": "newpassword123"
    }
    
    Returns: {
        "message": "Password reset successfully",
        "email": "customer@example.com"
    }
    """
    from django.contrib.auth.models import User
    
    email = request.data.get('email')
    otp = request.data.get('otp')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    
    # Validate required fields
    if not email:
        return Response({
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not otp:
        return Response({
            'error': 'OTP is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not new_password:
        return Response({
            'error': 'New password is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not confirm_password:
        return Response({
            'error': 'Password confirmation is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if passwords match
    if new_password != confirm_password:
        return Response({
            'error': 'Passwords do not match'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate password strength (basic validation)
    if len(new_password) < 8:
        return Response({
            'error': 'Password must be at least 8 characters long'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if customer with this email exists
    try:
        customer = Customer.objects.get(email=email)
    except Customer.DoesNotExist:
        return Response({
            'error': 'Customer with this email does not exist'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Verify OTP
    if not customer.otp or customer.otp != otp:
        return Response({
            'error': 'Invalid OTP'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if OTP is expired
    if not customer.is_otp_valid():
        customer.clear_otp()
        return Response({
            'error': 'OTP has expired. Please request a new one.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Reset password (customer must have a user account)
    if not customer.user:
        return Response({
            'error': 'Customer account is not linked to a user. Please contact support.'
        }, status=status.HTTP_400_BAD_REQUEST)
        
    customer.user.set_password(new_password)
    customer.user.save()
    
    # Clear OTP after successful password reset
    customer.clear_otp()
    
    return Response({
        'message': 'Password reset successfully',
        'email': email
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def get_rental_by_number_and_email(request):
    """
    Get rental details by rental number and customer email
    
    POST /vehicle-rental/api/customer/rental-details/
    Body: {
        "rental_number": 123,
        "email": "customer@example.com"
    }
    
    Returns complete rental details if the email matches the customer associated with the rental
    Includes: rental info, customer info, vehicle info, expenses, evaluation, and photos
    """
    rental_number = request.data.get('rental_number')
    email = request.data.get('email')
    
    # Validate required fields
    if not rental_number:
        return Response({
            'error': 'Número do aluguer é obrigatório'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not email:
        return Response({
            'error': 'Email é obrigatório'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Try to find the rental
    try:
        rental = Rental.objects.select_related(
            'vehicle', 
            'vehicle__brand', 
            'customer',
            'pickup_location',
            'return_location',
            'created_by'
        ).prefetch_related(
            'expenses',
            'expenses__category',
            'photos'
        ).get(id=rental_number)
    except Rental.DoesNotExist:
        return Response({
            'error': 'Aluguer não encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Verify that the email matches the customer's email
    if rental.customer.email.lower() != email.lower():
        return Response({
            'error': 'Email não corresponde ao cliente deste aluguer'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Fix empty total_amount if needed
    if not rental.total_amount and rental.daily_rate and rental.number_of_days:
        rental.subtotal = rental.daily_rate * rental.number_of_days
        rental.commission_amount = (rental.subtotal * rental.commission_percent) / 100 if rental.commission_percent else 0
        rental.total_amount = (
            rental.subtotal - 
            rental.commission_amount + 
            (rental.insurance_fee or 0) + 
            (rental.late_return_fee or 0) + 
            (rental.damage_fee or 0)
        )
        rental.save()
    
    # Serialize rental data using RentalSerializer (same as RentalViewSet)
    from .serializers import RentalSerializer, ExpenseSerializer, CustomerSerializer
    rental_data = RentalSerializer(rental, context={'request': request}).data
    
    # Get related expenses
    expenses = rental.expenses.select_related('category').order_by('-date')
    expenses_data = ExpenseSerializer(expenses, many=True, context={'request': request}).data
    
    # Get evaluation (if exists)
    evaluation = None
    try:
        if hasattr(rental, 'evaluation'):
            eval_obj = rental.evaluation
            evaluation = {
                'id': eval_obj.id,
                'overall_rating': eval_obj.overall_rating,
                'vehicle_cleanliness': eval_obj.vehicle_cleanliness,
                'vehicle_condition': eval_obj.vehicle_condition,
                'service_quality': eval_obj.service_quality,
                'value_for_money': eval_obj.value_for_money,
                'comments': eval_obj.comments,
                'created_at': eval_obj.created_at,
            }
    except RentalEvaluation.DoesNotExist:
        evaluation = None
    
    # Get photos
    start_photos = rental.photos.filter(photo_type__startswith='start_')
    return_photos = rental.photos.filter(photo_type__startswith='return_')
    
    start_photos_data = [{
        'id': photo.id,
        'photo_type': photo.photo_type,
        'image': request.build_absolute_uri(photo.image.url) if photo.image else None,
        'uploaded_at': photo.uploaded_at
    } for photo in start_photos]
    
    return_photos_data = [{
        'id': photo.id,
        'photo_type': photo.photo_type,
        'image': request.build_absolute_uri(photo.image.url) if photo.image else None,
        'uploaded_at': photo.uploaded_at
    } for photo in return_photos]
    
    # Customer data
    customer_data = CustomerSerializer(rental.customer, context={'request': request}).data
    
    # Build response in the same structure as rental_detail context
    response_data = {
        **rental_data,  # Spread all rental fields at root level
        'customer': customer_data,
        'expenses': expenses_data,
        'evaluation': evaluation,
        'start_photos_count': len(start_photos_data),
        'return_photos_count': len(return_photos_data),
        'start_photos': start_photos_data,
        'return_photos': return_photos_data,
    }
    
    return Response(response_data, status=status.HTTP_200_OK)


class SystemConfigurationAPIView(APIView):
    """
    API view for system configuration/rates 
    GET: Retrieve current configuration (no authentication required)
    """
    permission_classes = []  # No authentication required
    
    def get(self, request):
        """Get current system configuration"""
        try:
            config = SystemConfiguration.get_instance()
            serializer = SystemConfigurationSerializer(config)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve system configuration',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SystemConfigurationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for system configuration/rates - appears in Swagger
    GET: Retrieve current configuration (no authentication required)
    """
    queryset = SystemConfiguration.objects.all()
    serializer_class = SystemConfigurationSerializer
    permission_classes = []  # No authentication required
    
    def get_object(self):
        """Always return the singleton instance"""
        return SystemConfiguration.get_instance()
    
    def list(self, request, *args, **kwargs):
        """Return the singleton configuration"""
        config = self.get_object()
        serializer = self.get_serializer(config)
        return Response(serializer.data)


# ============================================================
# Parameterization Views (Gestão de Parametrizações)
# ============================================================

# --- Vehicle Brands ---
@login_required
def brand_list(request):
    brands = VehicleBrand.objects.all().annotate(vehicle_count=Count('vehicles'))
    context = {'brands': brands, 'segment': 'param_brands'}
    return render(request, 'vehicle_rental/param/brand_list.html', context)

@login_required
def brand_create(request):
    if request.method == 'POST':
        form = VehicleBrandForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Marca criada com sucesso.')
            return redirect('vehicle_rental:brand_list')
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = VehicleBrandForm()
    return render(request, 'vehicle_rental/param/brand_form.html', {'form': form, 'segment': 'param_brands', 'title': 'Nova Marca'})

@login_required
def brand_edit(request, pk):
    brand = get_object_or_404(VehicleBrand, pk=pk)
    if request.method == 'POST':
        form = VehicleBrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, 'Marca atualizada com sucesso.')
            return redirect('vehicle_rental:brand_list')
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = VehicleBrandForm(instance=brand)
    return render(request, 'vehicle_rental/param/brand_form.html', {'form': form, 'segment': 'param_brands', 'title': 'Editar Marca'})

@login_required
def brand_delete(request, pk):
    brand = get_object_or_404(VehicleBrand, pk=pk)
    if request.method == 'POST':
        brand.delete()
        messages.success(request, 'Marca eliminada com sucesso.')
    return redirect('vehicle_rental:brand_list')


# --- Delivery Locations ---
@login_required
def location_list(request):
    locations = DeliveryLocation.objects.all()
    context = {'locations': locations, 'segment': 'param_locations'}
    return render(request, 'vehicle_rental/param/location_list.html', context)

@login_required
def location_create(request):
    if request.method == 'POST':
        form = DeliveryLocationForm(request.POST)
        if form.is_valid():
            location = form.save(commit=False)
            location.created_by = request.user
            location.save()
            messages.success(request, 'Local criado com sucesso.')
            return redirect('vehicle_rental:location_list')
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = DeliveryLocationForm()
    return render(request, 'vehicle_rental/param/location_form.html', {'form': form, 'segment': 'param_locations', 'title': 'Novo Local'})

@login_required
def location_edit(request, pk):
    location = get_object_or_404(DeliveryLocation, pk=pk)
    if request.method == 'POST':
        form = DeliveryLocationForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            messages.success(request, 'Local atualizado com sucesso.')
            return redirect('vehicle_rental:location_list')
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = DeliveryLocationForm(instance=location)
    return render(request, 'vehicle_rental/param/location_form.html', {'form': form, 'segment': 'param_locations', 'title': 'Editar Local'})

@login_required
def location_delete(request, pk):
    location = get_object_or_404(DeliveryLocation, pk=pk)
    if request.method == 'POST':
        location.delete()
        messages.success(request, 'Local eliminado com sucesso.')
    return redirect('vehicle_rental:location_list')


# --- Expense Categories ---
@login_required
def expense_category_list(request):
    categories = ExpenseCategory.objects.all().annotate(expense_count=Count('expenses'))
    context = {'categories': categories, 'segment': 'param_expense_categories'}
    return render(request, 'vehicle_rental/param/expense_category_list.html', context)

@login_required
def expense_category_create(request):
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria criada com sucesso.')
            return redirect('vehicle_rental:expense_category_list')
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = ExpenseCategoryForm()
    return render(request, 'vehicle_rental/param/expense_category_form.html', {'form': form, 'segment': 'param_expense_categories', 'title': 'Nova Categoria'})

@login_required
def expense_category_edit(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk)
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria atualizada com sucesso.')
            return redirect('vehicle_rental:expense_category_list')
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = ExpenseCategoryForm(instance=category)
    return render(request, 'vehicle_rental/param/expense_category_form.html', {'form': form, 'segment': 'param_expense_categories', 'title': 'Editar Categoria'})

@login_required
def expense_category_delete(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Categoria eliminada com sucesso.')
    return redirect('vehicle_rental:expense_category_list')


# --- System Configuration ---
@login_required
def system_config_edit(request):
    config = SystemConfiguration.objects.first()
    if not config:
        config = SystemConfiguration.objects.create()
    if request.method == 'POST':
        form = SystemConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            messages.success(request, 'Configurações atualizadas com sucesso.')
            return redirect('vehicle_rental:system_config')
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = SystemConfigurationForm(instance=config)
    return render(request, 'vehicle_rental/param/system_config.html', {'form': form, 'config': config, 'segment': 'param_system_config'})


# --- Customer Notifications ---
@login_required
def notification_list(request):
    """List all customer notifications with filtering"""
    notifications = CustomerNotification.objects.select_related(
        'customer', 'rental', 'created_by'
    ).all()
    
    # Filtering
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    search_query = request.GET.get('q', '')
    
    if status_filter:
        notifications = notifications.filter(status=status_filter)
    
    if type_filter:
        notifications = notifications.filter(notification_type=type_filter)
    
    if search_query:
        notifications = notifications.filter(
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(recipient_email__icontains=search_query) |
            Q(subject__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(notifications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total': CustomerNotification.objects.count(),
        'sent': CustomerNotification.objects.filter(status='sent').count(),
        'failed': CustomerNotification.objects.filter(status='failed').count(),
        'pending': CustomerNotification.objects.filter(status='pending').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'notifications': page_obj.object_list,
        'stats': stats,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'search_query': search_query,
        'status_choices': CustomerNotification.STATUS_CHOICES,
        'type_choices': CustomerNotification.TYPE_CHOICES,
        'segment': 'notifications',
    }
    
    return render(request, 'vehicle_rental/notification_list.html', context)


@login_required
def notification_detail(request, pk):
    """View detailed notification information"""
    notification = get_object_or_404(
        CustomerNotification.objects.select_related('customer', 'rental', 'created_by'),
        pk=pk
    )
    
    context = {
        'notification': notification,
        'segment': 'notifications',
    }
    
    return render(request, 'vehicle_rental/notification_detail.html', context)


@login_required
def notification_resend(request, pk):
    """Resend a failed notification"""
    notification = get_object_or_404(CustomerNotification, pk=pk)
    
    if request.method == 'POST':
        success, error_msg = notification.send(user=request.user)
        
        if success:
            messages.success(request, f'Notificação #{notification.id} reenviada com sucesso!')
        else:
            messages.error(request, f'Erro ao reenviar notificação: {error_msg}')
        
        # Redirect based on referrer
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('vehicle_rental:notification_detail', pk=notification.pk)
    
    context = {
        'notification': notification,
        'segment': 'notifications',
    }
    
    return render(request, 'vehicle_rental/notification_resend_confirm.html', context)


@login_required
def evaluation_list(request):
    """List all rental evaluations with filtering and statistics"""
    evaluations = RentalEvaluation.objects.select_related(
        'rental__customer', 'rental__vehicle', 'rental__vehicle__brand'
    ).all().order_by('-created_at')
    
    # Filtering
    rating_filter = request.GET.get('rating', '')
    search_query = request.GET.get('q', '')
    vehicle_filter = request.GET.get('vehicle', '')
    
    if rating_filter:
        evaluations = evaluations.filter(overall_rating=rating_filter)
    
    if vehicle_filter:
        evaluations = evaluations.filter(rental__vehicle_id=vehicle_filter)
    
    if search_query:
        evaluations = evaluations.filter(
            Q(rental__customer__first_name__icontains=search_query) |
            Q(rental__customer__last_name__icontains=search_query) |
            Q(rental__vehicle__license_plate__icontains=search_query) |
            Q(comments__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(evaluations, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    from django.db.models import Avg, Count
    stats = {
        'total': RentalEvaluation.objects.count(),
        'avg_overall': RentalEvaluation.objects.aggregate(Avg('overall_rating'))['overall_rating__avg'] or 0,
        'avg_vehicle': RentalEvaluation.objects.aggregate(Avg('vehicle_condition_rating'))['vehicle_condition_rating__avg'] or 0,
        'avg_service': RentalEvaluation.objects.aggregate(Avg('service_quality_rating'))['service_quality_rating__avg'] or 0,
        'avg_value': RentalEvaluation.objects.aggregate(Avg('value_for_money_rating'))['value_for_money_rating__avg'] or 0,
        'would_recommend': RentalEvaluation.objects.filter(would_recommend=True).count(),
        'by_rating': {i: RentalEvaluation.objects.filter(overall_rating=i).count() for i in range(1, 6)},
    }
    
    context = {
        'page_obj': page_obj,
        'evaluations': page_obj.object_list,
        'stats': stats,
        'rating_filter': rating_filter,
        'vehicle_filter': vehicle_filter,
        'search_query': search_query,
        'rating_choices': RentalEvaluation.RATING_CHOICES,
        'segment': 'evaluations',
    }
    
    return render(request, 'vehicle_rental/evaluation_list.html', context)


# ===========================
# User Management Views (Staff Only)
# ===========================

@login_required
def user_list(request):
    """List all users - staff only"""
    if not request.user.is_staff:
        messages.error(request, 'Voc� n�o tem permiss�o para acessar esta p�gina.')
        return redirect('vehicle_rental:dashboard')
    
    # Only show staff users
    users = User.objects.filter(is_staff=True).order_by('-date_joined')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    context = {
        'users': users_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'segment': 'user_management',
    }
    
    return render(request, 'vehicle_rental/user_list.html', context)


@login_required
def user_detail(request, pk):
    """View details of a specific user - staff only"""
    if not request.user.is_staff:
        messages.error(request, 'Voc� n�o tem permiss�o para acessar esta p�gina.')
        return redirect('vehicle_rental:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    context = {
        'user_obj': user,
        'segment': 'user_management',
    }
    
    return render(request, 'vehicle_rental/user_detail.html', context)


@login_required
def user_create(request):
    """Create a new user - staff only"""
    if not request.user.is_staff:
        messages.error(request, 'Voc� n�o tem permiss�o para acessar esta p�gina.')
        return redirect('vehicle_rental:dashboard')
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Utilizador {user.username} criado com sucesso.')
            return redirect('vehicle_rental:user_detail', pk=user.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = UserCreateForm()
    
    context = {
        'form': form,
        'segment': 'user_management',
    }
    
    return render(request, 'vehicle_rental/user_form.html', context)


@login_required
def user_edit(request, pk):
    """Edit an existing user - staff only"""
    if not request.user.is_staff:
        messages.error(request, 'Voc� n�o tem permiss�o para acessar esta p�gina.')
        return redirect('vehicle_rental:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    # Prevent editing superuser unless current user is also superuser
    if user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Voc� n�o pode editar um superusu�rio.')
        return redirect('vehicle_rental:user_detail', pk=user.pk)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Utilizador {user.username} atualizado com sucesso.')
            return redirect('vehicle_rental:user_detail', pk=user.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = UserEditForm(instance=user)
    
    context = {
        'form': form,
        'user_obj': user,
        'segment': 'user_management',
    }
    
    return render(request, 'vehicle_rental/user_form.html', context)


@login_required
def user_delete(request, pk):
    """Delete a user - staff only"""
    if not request.user.is_staff:
        messages.error(request, 'Voc� n�o tem permiss�o para acessar esta p�gina.')
        return redirect('vehicle_rental:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    # Prevent deleting self
    if user == request.user:
        messages.error(request, 'Voc� n�o pode eliminar sua pr�pria conta.')
        return redirect('vehicle_rental:user_list')
    
    # Prevent deleting superuser unless current user is also superuser
    if user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Voc� n�o pode eliminar um superusu�rio.')
        return redirect('vehicle_rental:user_detail', pk=user.pk)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Utilizador {username} eliminado com sucesso.')
        return redirect('vehicle_rental:user_list')
    
    context = {
        'user_obj': user,
        'segment': 'user_management',
    }
    
    return render(request, 'vehicle_rental/user_delete_confirm.html', context)


@login_required
def user_toggle_active(request, pk):
    """Activate/deactivate a user - staff only"""
    if not request.user.is_staff:
        messages.error(request, 'Voc� n�o tem permiss�o para acessar esta p�gina.')
        return redirect('vehicle_rental:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    # Prevent toggling self
    if user == request.user:
        messages.error(request, 'Voc� n�o pode alterar o status da sua pr�pria conta.')
        return redirect('vehicle_rental:user_detail', pk=user.pk)
    
    # Prevent toggling superuser unless current user is also superuser
    if user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Voc� n�o pode alterar o status de um superusu�rio.')
        return redirect('vehicle_rental:user_detail', pk=user.pk)
    
    user.is_active = not user.is_active
    user.save()
    
    status = 'ativado' if user.is_active else 'desativado'
    messages.success(request, f'Utilizador {user.username} {status} com sucesso.')
    
    return redirect('vehicle_rental:user_detail', pk=user.pk)


@login_required
def user_change_password(request, pk):
    """Change a user'\''s password - staff only"""
    if not request.user.is_staff:
        messages.error(request, 'Voc� n�o tem permiss�o para acessar esta p�gina.')
        return redirect('vehicle_rental:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    # Prevent changing superuser password unless current user is also superuser
    if user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Voc� n�o pode alterar a password de um superusu�rio.')
        return redirect('vehicle_rental:user_detail', pk=user.pk)
    
    if request.method == 'POST':
        form = UserPasswordChangeForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            messages.success(request, f'Password do utilizador {user.username} alterada com sucesso.')
            return redirect('vehicle_rental:user_detail', pk=user.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = UserPasswordChangeForm()
    
    context = {
        'form': form,
        'user_obj': user,
        'segment': 'user_management',
    }
    
    return render(request, 'vehicle_rental/user_password_form.html', context)


@login_required
def user_permissions(request, pk):
    """Manage user permissions - staff only"""
    if not request.user.is_staff:
        messages.error(request, 'Voc� n�o tem permiss�o para acessar esta p�gina.')
        return redirect('vehicle_rental:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    # Prevent changing superuser permissions unless current user is also superuser
    if user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Voc� n�o pode alterar as permiss�es de um superusu�rio.')
        return redirect('vehicle_rental:user_detail', pk=user.pk)
    
    if request.method == 'POST':
        form = UserPermissionsForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Permissões do utilizador {user.username} atualizadas com sucesso.')
            return redirect('vehicle_rental:user_detail', pk=user.pk)
        else:
            add_form_errors_to_messages(request, form)
    else:
        form = UserPermissionsForm(instance=user)
    
    context = {
        'form': form,
        'user_obj': user,
        'segment': 'user_management',
    }
    
    return render(request, 'vehicle_rental/user_permissions_form.html', context)
