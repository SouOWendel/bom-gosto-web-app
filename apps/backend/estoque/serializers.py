from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from pedido.models import Produto
from .models import Estoque

<<<<<<< HEAD
# Formata lotes do Estoque e calcula os alertas de validade apresentados na API.
=======
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
class EstoqueSerializer(serializers.ModelSerializer):
    id_produto = serializers.PrimaryKeyRelatedField(
        queryset=Produto.objects.all(),
        source="produto",
    )
    vencido = serializers.SerializerMethodField()
<<<<<<< HEAD
    alerta_validade = serializers.SerializerMethodField()
=======
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8

    class Meta:
        model = Estoque
        fields = (
            "id_estoque",
            "id_produto",
            "quantidade_disponivel",
            "data_validade",
            "custo",
            "vencido",
<<<<<<< HEAD
            "alerta_validade",
=======
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
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

<<<<<<< HEAD
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
=======
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
class VerificarDisponibilidadeSerializer(serializers.Serializer):
    id_produto = serializers.PrimaryKeyRelatedField(
        queryset=Produto.objects.all(),
        source="produto",
    )
    quantidade = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
<<<<<<< HEAD
    )
=======
    )
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
