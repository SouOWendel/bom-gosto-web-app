from rest_framework.routers import DefaultRouter

from .views import CancelamentoViewSet, PedidoViewSet, ProdutoViewSet


# Registra as rotas de pedidos, produtos e consulta somente leitura dos cancelamentos.
router = DefaultRouter()
router.register("pedido", PedidoViewSet, basename="pedido")
router.register("cancelamento", CancelamentoViewSet, basename="cancelamento")
router.register("produtos", ProdutoViewSet, basename="produtos")
router.register("produto", ProdutoViewSet, basename="produto")

urlpatterns = router.urls
