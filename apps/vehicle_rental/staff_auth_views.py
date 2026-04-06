"""
View de autenticação customizada para o sistema de aluguel de veículos.
Restringe o login apenas para usuários staff ativos.
"""
from django.contrib.auth.views import LoginView
from .staff_auth_forms import StaffLoginForm


class StaffLoginView(LoginView):
    """
    View de login que permite apenas usuários staff.
    Usa StaffLoginForm que valida is_active=True AND is_staff=True.
    """
    template_name = 'accounts/login.html'
    form_class = StaffLoginForm
