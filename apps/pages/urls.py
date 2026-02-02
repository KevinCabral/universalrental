from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
  path('', views.index,  name='index'),
  
  # Profile URLs
  path('profile/', views.profile_view, name='profile'),
  path('profile/edit/', views.profile_edit, name='profile_edit'),
  path('profile/change-password/', views.change_password, name='change_password'),
]
