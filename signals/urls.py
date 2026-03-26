from django.urls import path
from . import views
urlpatterns=[
    path('',views.list_signalements),
    path('create/',views.create_signalement),
    path('report/', views.download_signalements_report),
    path('workspace/', views.workspace),
    path('feed/', views.activity_feed),
    path('<int:pk>/',views.detail_signalement),
    path('<int:pk>/valider/',views.valider_signalement),
    path('<int:pk>/commentaires/', views.add_comment),
    path('<int:pk>/reactions/', views.toggle_reaction),
    path('<int:pk>/favori/', views.toggle_favorite),
    path('narratifs/',views.list_narratifs),
    path('dashboard/',views.dashboard_stats),
]
