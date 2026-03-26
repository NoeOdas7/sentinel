from django.urls import path
from . import views
urlpatterns = [
    path('login/', views.login_step1),
    path('verify-otp/', views.verify_otp),
    path('resend-otp/', views.resend_otp),
    path('logout/', views.logout),
    path('register/', views.register),
    path('profile/', views.profile),
    path('sessions/', views.sessions),
    path('sessions/<int:sid>/revoke/', views.revoke_session),
    path('change-password/', views.change_password),
    path('invite/', views.invite),
    path('members/', views.members_list),
    path('members/<int:uid>/', views.update_member),
]
