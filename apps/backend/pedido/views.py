from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.db import transaction

from .models import Cancelamento, Pedido, status_operacional
from .serializers import CancelamentoRegistroSerializer, PedidoSerializer
from estoque.services import baixar_lotes
from producao.serializers import CancelamentoSerializer


# Bloqueia as rotas de pedidos até a senha provisória ser trocada.
class SenhaInicialAlterada(BasePermission):
    message = "Altere a senha inicial antes de acessar os pedidos."

    def has_permission(self, request, view):
        return not getattr(request.user, "primeiro_acesso", True)


# Oferece o CRUD de pedidos e as ações operacionais de consumo, conclusão e cancelamento.
class PedidoViewSet(ModelViewSet):
    queryset = Pedido.objects.all().order_by("-id_pedido")
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated, SenhaInicialAlterada]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    # Impede exclusões e preserva o histórico operacional do pedido.
    def perform_destroy(self, instance):
        raise ValidationError("Pedidos não podem ser excluídos; edite ou cancele o pedido.")

    # Dá baixa nos lotes válidos quando um pedido externo consumiu produto pronto.
    @action(detail=True, methods=["post"], url_path="consumir-estoque")
    @transaction.atomic
    def consumir_estoque(self, request, pk=None):
        pedido = Pedido.objects.select_for_update().get(pk=pk)
        pedido.status = status_operacional(pedido.status)
        if pedido.tipo != Pedido.Tipo.EXTERNO:
            return Response({"tipo": "A baixa por consumo é reservada a pedidos externos; a produção interna gera reposição."}, status=status.HTTP_400_BAD_REQUEST)
        if pedido.status not in (Pedido.Status.PEDIDO_FEITO, Pedido.Status.PRODUCAO_CONCLUIDA):
            return Response({"status": "Somente pedidos feitos ou com produção concluída podem consumir estoque."}, status=status.HTTP_400_BAD_REQUEST)
        if pedido.status == Pedido.Status.CONCLUIDO:
            return Response({"status": "O consumo deste pedido já foi confirmado."}, status=status.HTTP_400_BAD_REQUEST)
        from decimal import Decimal
        from producao.services import _receita_item
        from pedido.models import ReceitaProduto
        for item in pedido.itens.select_related("produto", "receita"):
            produto = item.produto
            receita = _receita_item(item)
            if produto is None and receita:
                produto = receita.produtos.order_by("id_produto").first()
                if produto is None:
                    relacao = ReceitaProduto.objects.filter(receita=receita).select_related("produto").first()
                    produto = relacao.produto if relacao else None
            if produto is None:
                raise ValidationError({"itens": "Não há produto pronto associado a um dos itens."})
            quantidade = Decimal(item.quantidade or item.quantidade_peso or 0)
            baixar_lotes(produto.pk, quantidade)
        pedido.status = Pedido.Status.CONCLUIDO
        pedido.save(update_fields=["status"])
        return Response(self.get_serializer(pedido).data)

    # Finaliza reposição interna sem retirar os lotes recém-produzidos do Estoque.
    @action(detail=True, methods=["post"], url_path="concluir")
    @transaction.atomic
    def concluir(self, request, pk=None):
        pedido = Pedido.objects.select_for_update().get(pk=pk)
        pedido.status = status_operacional(pedido.status)
        if pedido.tipo != Pedido.Tipo.INTERNO or pedido.status != Pedido.Status.PRODUCAO_CONCLUIDA:
            return Response({"status": "A conclusão direta é reservada à reposição interna após finalizar a produção."}, status=status.HTTP_400_BAD_REQUEST)
        pedido.status = Pedido.Status.CONCLUIDO
        pedido.save(update_fields=["status"])
        return Response(self.get_serializer(pedido).data)

    # Registra destino e consumos informados ao cancelar um pedido ainda aberto.
    @action(detail=True, methods=["post"], url_path="cancelar")
    @transaction.atomic
    def cancelar(self, request, pk=None):
        pedido = Pedido.objects.select_for_update().get(pk=pk)
        serializer = CancelamentoSerializer(data=request.data, context={"pedido": pedido})
        serializer.is_valid(raise_exception=True)
        pedido_cancelado, cancelamento = serializer.save()
        return Response(
            {
                "cancelamento": CancelamentoRegistroSerializer(cancelamento).data,
                "pedido": self.get_serializer(pedido_cancelado).data,
            },
            status=status.HTTP_200_OK,
        )


# Permite consultar os registros de cancelamento sem alterar ou excluir o histórico.
class CancelamentoViewSet(ReadOnlyModelViewSet):
    queryset = Cancelamento.objects.select_related("pedido").all().order_by("-id_cancelamento")
    serializer_class = CancelamentoRegistroSerializer
    permission_classes = [IsAuthenticated, SenhaInicialAlterada]
