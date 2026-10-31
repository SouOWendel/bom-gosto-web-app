from rest_framework.routers import DefaultRouter

from .views import IngredienteViewSet

# roteador que registra o viewset IngredienteViewSet, permitindo que os endpoints da API sejam automaticamente gerados com base nas rotas definidas no viewset, facilitando a criação de URLs RESTful para o módulo Inventario
router = DefaultRouter()
router.register("inventario/ingrediente", IngredienteViewSet, basename="ingrediente")

urlpatterns = router.urls
