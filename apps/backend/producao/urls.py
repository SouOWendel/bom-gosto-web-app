from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConcluirProducaoView, IniciarProducaoView, ReceitaViewSet, ValidarProducaoView

# Gera as rotas REST do cadastro de receitas.
router = DefaultRouter()
router.register("producao/receitas", ReceitaViewSet, basename="receita")

# Expõe ações por pedido para validar, iniciar e concluir a produção.
urlpatterns = [
    path("producao/pedidos/<int:pedido_id>/validar/", ValidarProducaoView.as_view(), name="validar-producao"),
    path("producao/pedidos/<int:pedido_id>/iniciar/", IniciarProducaoView.as_view(), name="iniciar-producao"),
    path("producao/pedidos/<int:pedido_id>/concluir/", ConcluirProducaoView.as_view(), name="concluir-producao"),
    path("", include(router.urls)),
]
