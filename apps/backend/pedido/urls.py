from rest_framework.routers import DefaultRouter

from .views import CancelamentoViewSet, PedidoViewSet


# Registra as rotas de pedidos e consulta somente leitura dos cancelamentos.
router = DefaultRouter()
router.register("pedido", PedidoViewSet, basename="pedido")
router.register("cancelamento", CancelamentoViewSet, basename="cancelamento")

urlpatterns = router.urls


