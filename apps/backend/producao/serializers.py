from decimal import Decimal

from rest_framework import serializers

from pedido.models import Produto
from .services import registrar_producao


class RegistrarProducaoSerializer(serializers.Serializer):
    produto_id = serializers.PrimaryKeyRelatedField(
        source="produto",
        queryset=Produto.objects.select_related("receita").all(),
    )
    quantidade_produzida = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    data_validade = serializers.DateField()
    custo = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )

    def create(self, validated_data):
        return registrar_producao(**validated_data)