from django.urls import path

from .views import RegistrarProducaoView

urlpatterns = [
    path("producao/", RegistrarProducaoView.as_view(), name="registrar-producao"),
]