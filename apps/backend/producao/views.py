from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from pedido.models import Pedido, Receita, status_operacional
from pedido.serializers import PedidoSerializer
from .serializers import ConcluirProducaoSerializer, ReceitaSerializer


# Restringe a Produção a usuários que já trocaram a senha provisória.
class SenhaInicialAlterada(BasePermission):
    message = "Altere a senha inicial antes de acessar a produção."

    def has_permission(self, request, view):
        return not getattr(request.user, "primeiro_acesso", True)


# Disponibiliza o CRUD de receitas e suas relações com ingredientes e produtos.
class ReceitaViewSet(ModelViewSet):
    queryset = Receita.objects.all().order_by("nome")
    serializer_class = ReceitaSerializer
    permission_classes = [IsAuthenticated, SenhaInicialAlterada]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    # Impede apagar receitas que ainda são referenciadas por itens de pedido.
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as erro:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("A receita está vinculada a itens de pedido e não pode ser excluída.") from erro


# Mostra disponibilidade e faltas de uma produção sem movimentar os saldos.
class ValidarProducaoView(APIView):
    permission_classes = [IsAuthenticated, SenhaInicialAlterada]

    # Devolve a análise atual do pedido para orientar a confeiteira.
    def post(self, request, pedido_id):
        from .services import analisar_pedido
        pedido = get_object_or_404(Pedido, pk=pedido_id)
        return Response(analisar_pedido(pedido))


# Muda o pedido para Em Produção sem baixar Inventário ou movimentar Estoque.
class IniciarProducaoView(APIView):
    permission_classes = [IsAuthenticated, SenhaInicialAlterada]

    # Autoriza o início somente quando o pedido ainda está em Pedido Feito.
    @transaction.atomic
    def post(self, request, pedido_id):
        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pedido_id)
        pedido.status = status_operacional(pedido.status)
        if pedido.status != Pedido.Status.PEDIDO_FEITO:
            return Response({"status": "A produção só pode ser iniciada para pedidos feitos."}, status=status.HTTP_400_BAD_REQUEST)
        pedido.status = Pedido.Status.EM_PRODUCAO
        pedido.save(update_fields=["status"])
        return Response(PedidoSerializer(pedido, context={"request": request}).data)


# Confirma consumos reais, validade, custo e entrada no Estoque por pedido.
class ConcluirProducaoView(APIView):
    permission_classes = [IsAuthenticated, SenhaInicialAlterada]

    # Valida os dados antes de executar as movimentações atômicas da conclusão.
    def post(self, request, pedido_id):
        pedido = get_object_or_404(Pedido, pk=pedido_id)
        serializer = ConcluirProducaoSerializer(data=request.data, context={"pedido": pedido})
        serializer.is_valid(raise_exception=True)
        resultado = serializer.save()
        return Response({"pedido": PedidoSerializer(resultado["pedido"], context={"request": request}).data, "custo_producao": resultado["custo"]}, status=status.HTTP_200_OK)
