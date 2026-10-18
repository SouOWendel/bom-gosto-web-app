from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import Ingrediente
from .serializers import IngredienteSerializer

# permite que apenas usuarios que ja alteraram a senha inicial possam acessar os endpoints do Inventario, garantindo que a politica de seguranca seja aplicada antes de permitir o acesso aos recursos da API
class SenhaInicialAlterada(BasePermission):
    message = "Altere a senha inicial antes de acessar o inventário."

    def has_permission(self, request, view):
        return not getattr(request.user, "primeiro_acesso", True)


class IngredienteViewSet(ModelViewSet):
    queryset = Ingrediente.objects.all().order_by("id_ingrediente")
    serializer_class = IngredienteSerializer
    permission_classes = [IsAuthenticated, SenhaInicialAlterada]
    # nao expor o metodo DELETE.
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
