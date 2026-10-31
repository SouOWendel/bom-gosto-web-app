from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from pedido.models import Produto
from .models import Estoque

# Formata lotes do Estoque e calcula os alertas de validade apresentados na API.
class EstoqueSerializer(serializers.ModelSerializer):
    id_produto = serializers.PrimaryKeyRelatedField(
        queryset=Produto.objects.all(),
        source="produto",
    )
    vencido = serializers.SerializerMethodField()
    alerta_validade = serializers.SerializerMethodField()

    class Meta:
        model = Estoque
        fields = (
            "id_estoque",
            "id_produto",
            "quantidade_disponivel",
            "data_validade",
            "custo",
            "vencido",
            "alerta_validade",
        )
        read_only_fields = ("id_estoque", "vencido")

    def validate_quantidade_disponivel(self, valor):
        if valor < 0:
            raise serializers.ValidationError(
                "A quantidade disponível não pode ser negativa."
            )
        return valor

    def validate_custo(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError(
                "O custo não pode ser negativo."
            )
        return valor

    def get_vencido(self, estoque):
        return (
            estoque.data_validade is not None
            and estoque.data_validade < timezone.localdate()
        )

    def get_alerta_validade(self, estoque):
        validade = estoque.data_validade
        if validade is None:
            return None
        dias = (validade - timezone.localdate()).days
        if dias <= 0:
            nivel = "critico"
        elif dias <= 7:
            nivel = "atencao"
        elif dias <= 15:
            nivel = "preventivo"
        else:
            return None
        return {"nivel": nivel, "dias_para_vencer": dias}

# Valida produto e quantidade recebidos na consulta de disponibilidade.
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
