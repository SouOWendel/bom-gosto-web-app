from decimal import Decimal

from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Estoque
from .serializers import EstoqueSerializer, VerificarDisponibilidadeSerializer

# classe que verifica se o usuario autenticado ja alterou a senha inicial, impedindo o acesso ao modulo Estoque (caso o usuario ainda esteja no estado de primeiro acesso), garantindo que a politica de segurança seja aplicada antes de permitir operacoes no estoque
class SenhaInicialAlterada(BasePermission):
    message = "Altere a senha inicial antes de acessar o estoque."

    def has_permission(self, request, view):
        return not getattr(request.user, "primeiro_acesso", True)

# classe que implementa o viewset para o modelo Estoque, fornecendo endpoints RESTful para listar, criar, atualizar e verificar a disponibilidade de lotes de estoque, com permissoes de acesso baseadas na autenticacao do usuario e na alteracao da senha inicial
class EstoqueViewSet(ModelViewSet):
    queryset = Estoque.objects.select_related("produto").all().order_by("id_estoque")
    serializer_class = EstoqueSerializer
    permission_classes = [IsAuthenticated, SenhaInicialAlterada]
    http_method_names = ["get", "put", "patch", "head", "options"] # nao permite excluir lotes de estoque

    # endpoint customizado que verifica a disponibilidade de um produto no estoque, recebendo o id do produto e a quantidade solicitada como parametros de consulta e retornando se ha saldo suficiente ou se deve encaminhar para producao
    @action(detail=False, methods=["get"], url_path="disponibilidade")
    def disponibilidade(self, request):
        consulta = VerificarDisponibilidadeSerializer(data=request.query_params)
        consulta.is_valid(raise_exception=True)

        produto = consulta.validated_data["produto"]
        id_produto = produto.id_produto
        quantidade_solicitada = consulta.validated_data["quantidade"]
        resultado = Estoque.objects.verificar_disponibilidade(
            id_produto,
            quantidade_solicitada,
        )

        # sem saldo suficiente de produto pronto, o fluxo deve seguir para Producao
        return Response(
            {
                "id_produto": id_produto,
                **resultado,
            }
        )
