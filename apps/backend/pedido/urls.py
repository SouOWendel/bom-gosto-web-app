from rest_framework.routers import DefaultRouter

<<<<<<< HEAD
from .views import CancelamentoViewSet, PedidoViewSet


# Registra as rotas de pedidos e consulta somente leitura dos cancelamentos.
router = DefaultRouter()
router.register("pedido", PedidoViewSet, basename="pedido")
router.register("cancelamento", CancelamentoViewSet, basename="cancelamento")
=======
from .views import PedidoViewSet


router = DefaultRouter()
router.register("pedido", PedidoViewSet, basename="pedido")
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8

urlpatterns = router.urls


