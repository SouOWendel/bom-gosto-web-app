from decimal import Decimal

from rest_framework import serializers

<<<<<<< HEAD
from inventario.models import Ingrediente
from pedido.models import Pedido, Produto, Receita, ReceitaProduto
from .models import IngredienteReceita
from .services import analisar_pedido, cancelar_pedido, concluir_producao


# Valida o ingrediente e a quantidade necessária na composição da receita.
class IngredienteReceitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngredienteReceita
        fields = ("id_ingrediente_receita", "ingrediente", "quantidade_necessaria")
        read_only_fields = ("id_ingrediente_receita",)

    def validate_quantidade_necessaria(self, valor):
        if valor <= 0:
            raise serializers.ValidationError("A quantidade deve ser maior que zero.")
        return valor


# Representa a relação já cadastrada entre receita e produto.
class ReceitaProdutoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceitaProduto
        fields = ("id_receita_produto", "produto", "quantidade", "unidade_medida", "custo_unitario")
        read_only_fields = ("id_receita_produto",)


# Valida os produtos e parâmetros da relação enviados ao editar uma receita.
class ReceitaProdutoEntradaSerializer(serializers.ModelSerializer):
    produto = serializers.PrimaryKeyRelatedField(queryset=Produto.objects.all())

    class Meta:
        model = ReceitaProduto
        fields = ("produto", "quantidade", "unidade_medida", "custo_unitario")

    def validate_quantidade(self, valor):
        if valor <= 0:
            raise serializers.ValidationError("A quantidade relacionada deve ser maior que zero.")
        return valor

    def validate_custo_unitario(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError("O custo não pode ser negativo.")
        return valor


# Cria e atualiza a receita junto com seus ingredientes e produtos relacionados.
class ReceitaSerializer(serializers.ModelSerializer):
    ingredientes = IngredienteReceitaSerializer(many=True, required=False, source="composicao")
    produtos_relacionados = ReceitaProdutoEntradaSerializer(many=True, required=False, write_only=True)
    produtos = serializers.SerializerMethodField()

    class Meta:
        model = Receita
        fields = ("id_receita", "nome", "rendimento_quantidade", "custo_calculado", "ingredientes", "produtos_relacionados", "produtos")
        read_only_fields = ("id_receita", "custo_calculado", "produtos")

    def get_produtos(self, receita):
        return ReceitaProdutoSerializer(ReceitaProduto.objects.filter(receita=receita).select_related("produto"), many=True).data

    def validate_rendimento_quantidade(self, valor):
        if valor is not None and valor <= 0:
            raise serializers.ValidationError("O rendimento deve ser maior que zero.")
        return valor

    def validate(self, attrs):
        ingredientes = attrs.get("composicao", [])
        ids_ingredientes = [linha["ingrediente"].pk for linha in ingredientes]
        if len(ids_ingredientes) != len(set(ids_ingredientes)):
            raise serializers.ValidationError({"ingredientes": "Cada ingrediente pode aparecer uma vez na receita."})
        produtos = attrs.get("produtos_relacionados", [])
        ids_produtos = [linha["produto"].pk for linha in produtos]
        if len(ids_produtos) != len(set(ids_produtos)):
            raise serializers.ValidationError({"produtos_relacionados": "Cada produto pode aparecer uma vez na receita."})
        return attrs

    # Grava a receita e suas relações na mesma transação.
    def create(self, validated_data):
        from django.db import transaction
        ingredientes = validated_data.pop("composicao", [])
        produtos = validated_data.pop("produtos_relacionados", [])
        with transaction.atomic():
            receita = Receita.objects.create(**validated_data)
            for item in ingredientes:
                IngredienteReceita.objects.create(receita=receita, **item)
            for relacao in produtos:
                produto = relacao.pop("produto")
                ReceitaProduto.objects.update_or_create(receita=receita, produto=produto, defaults=relacao)
        return receita

    # Atualiza relações aninhadas quando recebidas, preservando as omitidas.
    def update(self, instance, validated_data):
        from django.db import transaction
        ingredientes = validated_data.pop("composicao", None)
        produtos = validated_data.pop("produtos_relacionados", None)
        with transaction.atomic():
            for campo, valor in validated_data.items():
                setattr(instance, campo, valor)
            instance.save()
            if ingredientes is not None:
                IngredienteReceita.objects.filter(receita=instance).delete()
                for item in ingredientes:
                    IngredienteReceita.objects.create(receita=instance, **item)
            if produtos is not None:
                produtos_ids = [relacao["produto"].pk for relacao in produtos]
                ReceitaProduto.objects.filter(receita=instance).exclude(produto_id__in=produtos_ids).delete()
                for relacao in produtos:
                    produto = relacao.pop("produto")
                    ReceitaProduto.objects.update_or_create(receita=instance, produto=produto, defaults=relacao)
        return instance


# Valida o ingrediente e a quantidade real informados na produção ou cancelamento.
class ConsumoSerializer(serializers.Serializer):
    ingrediente_id = serializers.PrimaryKeyRelatedField(source="ingrediente", queryset=Ingrediente.objects.all())
    quantidade = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))

    def to_representation(self, instance):
        return {"ingrediente_id": instance["ingrediente"].pk, "quantidade": instance["quantidade"]}


# Recebe validade e consumos reais para concluir a produção de um pedido.
class ConcluirProducaoSerializer(serializers.Serializer):
    data_validade = serializers.DateField()
    consumos = ConsumoSerializer(many=True, allow_empty=False)

    # Converte os ingredientes validados em IDs antes de iniciar as movimentações.
    def create(self, validated_data):
        # IDs já são resolvidos pelo serializer para devolver erros claros antes da movimentação.
        consumos = [{"ingrediente_id": c["ingrediente"].pk, "quantidade": c["quantidade"]} for c in validated_data["consumos"]]
        return concluir_producao(self.context["pedido"], consumos, validated_data["data_validade"])


# Valida os dados necessários para cadastrar o produto reaproveitado.
class ProdutoAproveitadoSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=100)
    quantidade = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    data_validade = serializers.DateField()
    preco_venda = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))
    custo = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))


# Valida o destino e os consumos antes de registrar o cancelamento.
class CancelamentoSerializer(serializers.Serializer):
    consumos = ConsumoSerializer(many=True, allow_empty=True)
    destino = serializers.ChoiceField(choices=(("descarte", "Descarte"), ("estoque", "Estoque")))
    produto_aproveitado = ProdutoAproveitadoSerializer(required=False)

    def validate(self, attrs):
        if attrs["destino"] == "estoque" and not attrs.get("produto_aproveitado"):
            raise serializers.ValidationError({"produto_aproveitado": "Informe nome, quantidade, validade e preço de venda."})
        return attrs

    def save(self, **kwargs):
        consumos = [{"ingrediente_id": c["ingrediente"].pk, "quantidade": c["quantidade"]} for c in self.validated_data["consumos"]]
        return cancelar_pedido(self.context["pedido"], consumos, self.validated_data["destino"], self.validated_data.get("produto_aproveitado"))


# Valida a referência de pedido usada para solicitar uma análise de produção.
class AnaliseProducaoSerializer(serializers.Serializer):
    pedido_id = serializers.PrimaryKeyRelatedField(source="pedido", queryset=Pedido.objects.all())

    def to_representation(self, instance):
        return analisar_pedido(instance["pedido"])
=======
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
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
