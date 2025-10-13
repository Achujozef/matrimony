from django.urls import path
from .views import *

urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),

    path('', DashboardView.as_view(), name='dashboard'),
    path('profile/<int:pk>/', ProfileDetailView.as_view(), name='profile_detail'),
    path('profile/<int:pk>/interest/', express_interest_view, name='express_interest'),
    path('profile/<int:pk>/reveal-contact/', reveal_contact_view, name='reveal_contact'),


    path('interest/<int:pk>/accept/', accept_interest, name='accept_interest'),
    path('interest/<int:pk>/reject/', reject_interest, name='reject_interest'),
]
