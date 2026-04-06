"""
Formulário de autenticação customizado para o sistema de aluguel de veículos.
Restringe o login apenas para usuários staff ativos.
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.utils.translation import gettext_lazy as _


class StaffLoginForm(AuthenticationForm):
    """
    Formulário de login que permite apenas usuários staff.
    Requer: is_active=True AND is_staff=True
    """
    username = UsernameField(
        label=_("Your Username"), 
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"})
    )
    password = forms.CharField(
        label=_("Your Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
    )

    def confirm_login_allowed(self, user):
        """
        Controla se o usuário pode fazer login.
        Permite apenas usuários ativos E staff.
        """
        if not user.is_active:
            raise forms.ValidationError(
                _("Esta conta está inativa. Contacte o administrador."),
                code='inactive',
            )
        
        if not user.is_staff:
            raise forms.ValidationError(
                _("Acesso negado. Apenas colaboradores podem acessar o sistema."),
                code='not_staff',
            )
