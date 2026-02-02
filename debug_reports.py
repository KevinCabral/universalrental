import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.vehicle_rental.models import *
from django.db.models import Sum, Count, Q
from datetime import date, timedelta

print("=== DEBUG REPORTS DASHBOARD ===")

# Check current date and default range
today = date.today()
date_from = today.replace(day=1)  # Start of current month
date_to = today

print(f"Date range: {date_from} to {date_to}")
print(f"Today: {today}")

# Check rentals in range
rentals_qs = Rental.objects.filter(start_date__date__range=[date_from, date_to])
print(f"\nRentals in range: {rentals_qs.count()}")

# Check expenses in range  
expenses_qs = Expense.objects.filter(date__range=[date_from, date_to])
print(f"Expenses in range: {expenses_qs.count()}")

# Test expense breakdown query
print("\n=== EXPENSE BREAKDOWN DEBUG ===")
expense_breakdown = ExpenseCategory.objects.annotate(
    total_amount=Sum('expenses__amount', filter=Q(expenses__date__range=[date_from, date_to]))
).exclude(total_amount__isnull=True).exclude(total_amount=0)

print(f"Expense categories with data: {expense_breakdown.count()}")
for exp in expense_breakdown[:5]:
    print(f"  {exp.name}: €{exp.total_amount}")

# Test monthly revenue
print("\n=== MONTHLY REVENUE DEBUG ===")
monthly_data = []
for i in range(3):  # Last 3 months
    month_date = today.replace(day=1) - timedelta(days=30 * i)
    month_start = month_date.replace(day=1)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
    
    month_rentals = Rental.objects.filter(start_date__date__range=[month_start, month_end])
    revenue = month_rentals.aggregate(total=Sum('total_amount'))['total'] or 0
    commission = month_rentals.aggregate(total=Sum('commission_amount'))['total'] or 0
    
    print(f"{month_start.strftime('%b %Y')}: {month_rentals.count()} rentals, Revenue: €{revenue}, Commission: €{commission}")
    monthly_data.append({
        'month': month_start.strftime('%b %Y'),
        'revenue': float(revenue),
        'commission': float(commission)
    })

print(f"\nMonthly data structure: {monthly_data}")

# Test all categories
print("\n=== ALL EXPENSE CATEGORIES ===")
all_categories = ExpenseCategory.objects.all()
for cat in all_categories:
    total_ever = cat.expenses.aggregate(total=Sum('amount'))['total'] or 0
    total_in_range = cat.expenses.filter(date__range=[date_from, date_to]).aggregate(total=Sum('amount'))['total'] or 0
    print(f"{cat.name}: Total ever: €{total_ever}, In range: €{total_in_range}")
