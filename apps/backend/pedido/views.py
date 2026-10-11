from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import Pedido
from .serializers import PedidoSerializer


class SenhaInicialAlterada(BasePermission):
    message = "Altere a senha inicial antes de acessar os pedidos."

    def has_permission(self, request, view):
        return not getattr(request.user, "primeiro_acesso", True)


class PedidoViewSet(ModelViewSet):
    queryset = Pedido.objects.all().order_by("-id_pedido")
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated, SenhaInicialAlterada]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]


