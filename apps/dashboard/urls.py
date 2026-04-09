from django.urls import path

from . import views


urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("ayuda/", views.ayuda, name="ayuda"),
    path("configuracion/", views.configuracion, name="configuracion"),
]
