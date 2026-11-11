from datetime import date
from decimal import Decimal, InvalidOperation

from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from core.permissions import SenhaInicialAlterada
from producao.services import recalcular_receitas_do_ingrediente
from .models import Ingrediente
from .serializers import IngredienteSerializer


# Permite cadastrar, consultar e editar os ingredientes do Inventário.
class IngredienteViewSet(ModelViewSet):
    queryset = Ingrediente.objects.all().order_by("id_ingrediente")
    serializer_class = IngredienteSerializer
    permission_classes = [IsAuthenticated, SenhaInicialAlterada]
    # nao expor o metodo DELETE.
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    # Um novo custo unitário muda o custo das receitas que usam o insumo.
    def perform_update(self, serializer):
        custo_anterior = serializer.instance.custo_unitario
        ingrediente = serializer.save()
        if ingrediente.custo_unitario != custo_anterior:
            recalcular_receitas_do_ingrediente(ingrediente)

    @action(detail=True, methods=["post"], url_path="movimentar")
    @transaction.atomic
    def movimentar(self, request, pk=None):
        ingrediente = self.get_object()
        tipo = request.data.get("tipo")
        try:
            quantidade = Decimal(str(request.data.get("quantidade", "")))
        except (InvalidOperation, TypeError):
            raise ValidationError({"quantidade": "Informe uma quantidade válida."})

        if quantidade <= 0:
            raise ValidationError({"quantidade": "A quantidade deve ser maior que zero."})
        if tipo not in ("entrada", "saida"):
            raise ValidationError({"tipo": "Informe entrada ou saida."})

        saldo_atual = ingrediente.quantidade_disponivel
        if tipo == "saida":
            if saldo_atual is None:
                raise ValidationError(
                    {"quantidade": "Não há saldo disponível para registrar uma saída."}
                )
            if quantidade > saldo_atual:
                raise ValidationError(
                    {"quantidade": "A saída não pode ser maior que o saldo disponível."}
                )
            ingrediente.quantidade_disponivel = saldo_atual - quantidade
        else:
            ingrediente.quantidade_disponivel = (saldo_atual or Decimal("0")) + quantidade
            if "custo_unitario" in request.data:
                custo = request.data.get("custo_unitario")
                if custo in (None, ""):
                    ingrediente.custo_unitario = None
                else:
                    try:
                        custo_decimal = Decimal(str(custo))
                    except (InvalidOperation, TypeError):
                        raise ValidationError(
                            {"custo_unitario": "Informe um custo unitário válido."}
                        )
                    if custo_decimal < 0:
                        raise ValidationError(
                            {"custo_unitario": "O custo unitário não pode ser negativo."}
                        )
                    ingrediente.custo_unitario = custo_decimal
            if "data_validade" in request.data:
                validade = request.data.get("data_validade")
                if validade in (None, ""):
                    ingrediente.data_validade = None
                else:
                    try:
                        ingrediente.data_validade = date.fromisoformat(str(validade))
                    except ValueError:
                        raise ValidationError(
                            {"data_validade": "Informe uma data de validade válida."}
                        )

        ingrediente.save(update_fields=[
            "quantidade_disponivel",
            "custo_unitario",
            "data_validade",
        ])
        return Response(self.get_serializer(ingrediente).data)
