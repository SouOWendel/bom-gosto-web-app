from rest_framework.routers import DefaultRouter

from .views import EstoqueViewSet

# roteador que registra o viewset EstoqueViewSet, permitindo que os endpoints da API sejam automaticamente gerados com base nas rotas definidas no viewset, facilitando a criação de URLs RESTful para o módulo Estoque
router = DefaultRouter()
router.register("estoque", EstoqueViewSet, basename="estoque")

urlpatterns = router.urls
