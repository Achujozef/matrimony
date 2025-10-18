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

    path("my-profile/", my_profile_view, name="my_profile"),
    path("premium/", premium_view, name="premium"),
    path('matches/', MatchedProfilesView.as_view(), name='matches_list'),
    path('interest/cancel/<int:interest_id>/', CancelSentInterestView.as_view(), name='cancel_sent_interest'),
    path('match/cancel/<int:match_id>/', CancelMatchView.as_view(), name='cancel_match'),
    path('interest/<int:pk>/accept/', accept_interest, name='accept_interest'),
    path('interest/<int:pk>/reject/', reject_interest, name='reject_interest'),

    path('president/login/', ShakhaPresidentLoginView.as_view(), name='shakha_login'),
    path('president/logout/', shakha_logout, name='shakha_logout'),
    path('president/dashboard/', president_dashboard, name='president_dashboard'),
    path('president/profile/<int:pk>/', view_profile, name='view_profile'),
    path('president/approve/<int:pk>/', approve_profile, name='approve_profile'),
    path('president/block/<int:pk>/', block_profile, name='block_profile'),
    path('update-profile-status/<int:pk>/', update_profile_status, name='update_profile_status'),


]
