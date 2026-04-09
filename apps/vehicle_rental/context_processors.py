"""
Context processors for vehicle_rental app
Adds global context variables to all templates
"""
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .models import CustomerNotification, Rental


def notifications(request):
    """
    Add recent notifications to template context
    Returns unread notifications for staff users
    """
    context = {
        'recent_notifications': [],
        'unread_count': 0,
    }
    
    # Only show notifications for authenticated staff users
    if request.user.is_authenticated and request.user.is_staff:
        # Get recent notifications from the last 7 days
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        # Get all recent notifications (sent successfully)
        recent_notifs = CustomerNotification.objects.filter(
            status='sent',
            created_at__gte=seven_days_ago
        ).select_related('customer', 'rental').order_by('-created_at')[:10]
        
        # Format notifications for display
        formatted_notifications = []
        for notif in recent_notifs:
            # Determine icon and color based on notification type
            if notif.notification_type == 'rental_booking':
                icon = 'car'
                color = 'primary'
                title = 'Nova Reserva'
            elif notif.notification_type == 'customer_welcome':
                icon = 'user-plus'
                color = 'success'
                title = 'Novo Cliente'
            elif notif.notification_type == 'rental_confirmation':
                icon = 'check-circle'
                color = 'success'
                title = 'Reserva Confirmada'
            elif notif.notification_type == 'rental_return':
                icon = 'truck'
                color = 'info'
                title = 'Devolução'
            elif notif.notification_type == 'rental_cancellation':
                icon = 'x-circle'
                color = 'danger'
                title = 'Cancelamento'
            elif notif.notification_type == 'payment_confirmation':
                icon = 'dollar-sign'
                color = 'success'
                title = 'Pagamento'
            else:
                icon = 'bell'
                color = 'secondary'
                title = 'Notificação'
            
            # Calculate time ago
            time_diff = timezone.now() - notif.created_at
            if time_diff.seconds < 60:
                time_ago = 'Agora mesmo'
            elif time_diff.seconds < 3600:
                minutes = time_diff.seconds // 60
                time_ago = f'{minutes} min atrás'
            elif time_diff.seconds < 86400:
                hours = time_diff.seconds // 3600
                time_ago = f'{hours} hora{"s" if hours > 1 else ""} atrás'
            else:
                days = time_diff.days
                time_ago = f'{days} dia{"s" if days > 1 else ""} atrás'
            
            # Create message
            if notif.rental:
                message = f'{notif.customer.full_name} - {notif.rental.vehicle.brand.name} {notif.rental.vehicle.model}'
            else:
                message = f'{notif.customer.full_name} - {notif.subject}'
            
            formatted_notifications.append({
                'id': notif.id,
                'icon': icon,
                'color': color,
                'title': title,
                'message': message,
                'time_ago': time_ago,
                'created_at': notif.created_at,
                'is_today': notif.created_at.date() == timezone.now().date(),
            })
        
        context['recent_notifications'] = formatted_notifications
        context['unread_count'] = len(formatted_notifications)
    
    return context
