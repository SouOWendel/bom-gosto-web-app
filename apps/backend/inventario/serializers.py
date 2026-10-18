from rest_framework import serializers

from .models import Ingrediente

# requisito do modulo Inventario: cadastrar materias-primas e acompanhar quantidade, custo de aquisicao e limite minimo
# os nomes seguem as colunas da tabela Ingrediente em database/create_schema.sql
class IngredienteSerializer(serializers.ModelSerializer):
    # campo calculado para indicar se a quantidade disponivel está abaixo do minimo
    # SerializerMethodField é usado para criar campos que nao existem no modelo, mas sao derivados de outros campos ou calculos, evitando a necessidade de armazenar dados redundantes no banco de dados
    abaixo_do_minimo = serializers.SerializerMethodField()

    class Meta:
        model = Ingrediente
        fields = (
            "id_ingrediente",
            "nome",
            "quantidade_disponivel",
            "custo_unitario",
            "data_validade",
            "quantidade_minima",
            "abaixo_do_minimo",
        )
        read_only_fields = ("id_ingrediente",)

    # evita um saldo negativo, que nao representa quantidade disponivel
    def validate_quantidade_disponivel(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError(
                "A quantidade disponível não pode ser negativa."
            )
        return valor

    # o custo unitario cadastrado para aquisicao nao pode ser negativo
    def validate_custo_unitario(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError("O custo unitário não pode ser negativo.")
        return valor

    # o limite minimo de seguranca é uma quantidade, portanto nao pode ser negativa
    def validate_quantidade_minima(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError(
                "A quantidade mínima não pode ser negativa."
            )
        return valor

    # requisito do Inventario: alertar quando o ingrediente estiver abaixo do minimo
    def get_abaixo_do_minimo(self, ingrediente):
        quantidade = ingrediente.quantidade_disponivel
        quantidade_minima = ingrediente.quantidade_minima
        if quantidade is None or quantidade_minima is None:
            return None
        return quantidade < quantidade_minima
