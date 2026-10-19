from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from pedido.models import Produto

from .models import Estoque


class EstoqueSerializer(serializers.ModelSerializer):
    id_produto = serializers.PrimaryKeyRelatedField(
        queryset=Produto.objects.all(),
        source="produto",
    )
    vencido = serializers.SerializerMethodField()

    class Meta:
        model = Estoque
        fields = (
            "id_estoque",
            "id_produto",
            "quantidade_disponivel",
            "data_validade",
            "custo",
            "vencido",
        )
        read_only_fields = ("id_estoque", "vencido")

    # saldos negativos nao podem representar produto pronto disponivel para um pedido
    def validate_quantidade_disponivel(self, valor):
        if valor < 0:
            raise serializers.ValidationError(
                "A quantidade disponível não pode ser negativa."
            )
        return valor

    # o custo do lote representa custo de producao, nao um valor negativo
    def validate_custo(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError("O custo não pode ser negativo.")
        return valor

    # a validade integra o controle de produtos prontos. o campo é derivado para expor ao usuario se este lote ja venceu, sem gravar dado duplicado
    def get_vencido(self, estoque):
        return (
            estoque.data_validade is not None
            and estoque.data_validade < timezone.localdate()
        )

# o pedido consulta o produto e a quantidade necessaria para verificar se ha saldo de produto pronto ou se deve encaminhar o item a Producao
class VerificarDisponibilidadeSerializer(serializers.Serializer):
    id_produto = serializers.PrimaryKeyRelatedField(
        queryset=Produto.objects.all(),
        source="produto",
    )
    quantidade = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
