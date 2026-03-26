from django.urls import path
from . import views
urlpatterns=[
    path('',views.list_acteurs),
    path('create/',views.create_acteur),
    path('<int:pk>/download/',views.download_acteur_profile),
    path('<int:pk>/',views.detail_acteur),
    path('network/',views.network_data),
]
