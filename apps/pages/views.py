from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q, Avg, F
from django.utils import timezone
from decimal import Decimal
from apps.pages.models import Product
from django.core import serializers

from .models import *

@login_required
def index(request):
  from apps.vehicle_rental.models import Vehicle, Customer, Rental, Expense, MaintenanceRecord

  now = timezone.now()
  current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
  if now.month == 12:
      next_month_start = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
  else:
      next_month_start = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)

  # Vehicle stats
  total_vehicles = Vehicle.objects.filter(is_active=True).count()
  available_vehicles = Vehicle.objects.filter(is_active=True, status='available').count()
  rented_vehicles = Vehicle.objects.filter(is_active=True, status='rented').count()
  maintenance_vehicles = Vehicle.objects.filter(is_active=True, status='maintenance').count()

  # Customer stats
  total_customers = Customer.objects.count()
  new_customers_month = Customer.objects.filter(created_at__gte=current_month_start).count()

  # Rental stats
  total_rentals = Rental.objects.count()
  active_rentals = Rental.objects.filter(status='active').count()
  pending_rentals = Rental.objects.filter(status='pending').count()
  completed_rentals = Rental.objects.filter(status='completed').count()
  overdue_rentals = Rental.objects.filter(status='active', end_date__lt=now).count()

  # Monthly revenue
  monthly_revenue = Rental.objects.filter(
      status__in=['active', 'completed'],
      created_at__gte=current_month_start,
      created_at__lt=next_month_start,
  ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

  # Total revenue (all time)
  total_revenue = Rental.objects.filter(
      status__in=['active', 'completed'],
  ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

  # Monthly expenses
  monthly_expenses = Expense.objects.filter(
      date__gte=current_month_start.date(),
      date__lt=next_month_start.date(),
  ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

  # Monthly profit
  monthly_profit = monthly_revenue - monthly_expenses

  # Rentals this month
  rentals_this_month = Rental.objects.filter(
      created_at__gte=current_month_start,
      created_at__lt=next_month_start,
  ).count()

  # Best customer (most rentals)
  best_customer = Customer.objects.annotate(
      rental_count=Count('rentals', filter=Q(rentals__status__in=['active', 'completed'])),
      total_spent=Sum('rentals__total_amount', filter=Q(rentals__status__in=['active', 'completed']))
  ).order_by('-rental_count').first()

  # Most rented vehicle
  most_rented_vehicle = Vehicle.objects.annotate(
      rental_count=Count('rentals', filter=Q(rentals__status__in=['active', 'completed']))
  ).order_by('-rental_count').first()

  # Average rental duration
  avg_duration = Rental.objects.filter(
      status__in=['active', 'completed']
  ).aggregate(avg=Avg('number_of_days'))['avg'] or 0

  # Average daily rate
  avg_daily_rate = Rental.objects.filter(
      status__in=['active', 'completed']
  ).aggregate(avg=Avg('daily_rate'))['avg'] or Decimal('0')

  # Recent rentals (last 10)
  recent_rentals = Rental.objects.select_related(
      'vehicle', 'vehicle__brand', 'customer'
  ).order_by('-created_at')[:10]

  # Upcoming returns (next 7 days)
  upcoming_returns = Rental.objects.filter(
      status='active',
      end_date__gte=now,
      end_date__lte=now + timezone.timedelta(days=7),
  ).select_related('vehicle', 'vehicle__brand', 'customer').order_by('end_date')[:5]

  # Occupancy rate
  occupancy_rate = round((rented_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0, 1)

  # Monthly revenue by last 6 months for chart
  monthly_chart_data = []
  monthly_chart_labels = []
  for i in range(5, -1, -1):
      month = now.month - i
      year = now.year
      if month <= 0:
          month += 12
          year -= 1
      month_start = now.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
      if month == 12:
          month_end = now.replace(year=year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
      else:
          month_end = now.replace(year=year, month=month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
      
      rev = Rental.objects.filter(
          status__in=['active', 'completed'],
          created_at__gte=month_start,
          created_at__lt=month_end,
      ).aggregate(total=Sum('total_amount'))['total'] or 0
      monthly_chart_data.append(float(rev))
      month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
      monthly_chart_labels.append(month_names[month - 1])

  context = {
    'segment': 'dashboard',
    'total_vehicles': total_vehicles,
    'available_vehicles': available_vehicles,
    'rented_vehicles': rented_vehicles,
    'maintenance_vehicles': maintenance_vehicles,
    'total_customers': total_customers,
    'new_customers_month': new_customers_month,
    'total_rentals': total_rentals,
    'active_rentals': active_rentals,
    'pending_rentals': pending_rentals,
    'completed_rentals': completed_rentals,
    'overdue_rentals': overdue_rentals,
    'monthly_revenue': monthly_revenue,
    'total_revenue': total_revenue,
    'monthly_expenses': monthly_expenses,
    'monthly_profit': monthly_profit,
    'rentals_this_month': rentals_this_month,
    'best_customer': best_customer,
    'most_rented_vehicle': most_rented_vehicle,
    'avg_duration': round(avg_duration, 1),
    'avg_daily_rate': avg_daily_rate,
    'recent_rentals': recent_rentals,
    'upcoming_returns': upcoming_returns,
    'occupancy_rate': occupancy_rate,
    'monthly_chart_data': monthly_chart_data,
    'monthly_chart_labels': monthly_chart_labels,
  }
  return render(request, "pages/index.html", context)

# Components
def color(request):
  context = {
    'segment': 'color'
  }
  return render(request, "pages/color.html", context)

def typography(request):
  context = {
    'segment': 'typography'
  }
  return render(request, "pages/typography.html", context)

def icon_feather(request):
  context = {
    'segment': 'feather_icon'
  }
  return render(request, "pages/icon-feather.html", context)

def sample_page(request):
  context = {
    'segment': 'sample_page',
  }
  return render(request, 'pages/sample-page.html', context)

@login_required
def profile_view(request):
  context = {
    'segment': 'profile',
    'user': request.user
  }
  return render(request, 'pages/profile.html', context)

@login_required
def profile_edit(request):
  if request.method == 'POST':
    user = request.user
    user.first_name = request.POST.get('first_name', '')
    user.last_name = request.POST.get('last_name', '')
    user.email = request.POST.get('email', '')
    user.save()
    messages.success(request, 'Perfil atualizado com sucesso!')
    return redirect('profile')
  
  context = {
    'segment': 'profile_edit',
    'user': request.user
  }
  return render(request, 'pages/profile-edit.html', context)

@login_required
def change_password(request):
  if request.method == 'POST':
    form = PasswordChangeForm(request.user, request.POST)
    if form.is_valid():
      user = form.save()
      update_session_auth_hash(request, user)  # Important!
      messages.success(request, 'Senha alterada com sucesso!')
      return redirect('profile')
    else:
      messages.error(request, 'Por favor, corrija os erros abaixo.')
  else:
    form = PasswordChangeForm(request.user)
  
  context = {
    'segment': 'change_password',
    'form': form
  }
  return render(request, 'pages/change-password.html', context)
