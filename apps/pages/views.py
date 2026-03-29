from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.models import User
from apps.pages.models import Product
from django.core import serializers

from .models import *

@login_required
def index(request):
  context = {
    'segment': 'dashboard'
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
