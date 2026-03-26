from django.urls import path
from . import views
urlpatterns=[
    path('',views.list_ressources),
    path('create/',views.create_ressource),
    path('<int:pk>/valider/',views.valider_ressource),
]
