from rest_framework.routers import DefaultRouter

from .views import PedidoViewSet


router = DefaultRouter()
router.register("pedido", PedidoViewSet, basename="pedido")

urlpatterns = router.urls


