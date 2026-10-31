from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from rest_framework import serializers

from estoque.models import Estoque

<<<<<<< HEAD
from .models import Cancelamento, Cliente, ItemPedido, Pedido, status_operacional
from producao.services import analisar_pedido


# Devolve os dados do registro de cancelamento para consulta pela API.
class CancelamentoRegistroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cancelamento
        fields = ("id_cancelamento", "pedido", "destino", "data_cancelamento")
        read_only_fields = fields


# Valida os dados de cada item e apresenta sua disponibilidade em Estoque.
=======
from .models import ItemPedido, Pedido


>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
class ItemPedidoSerializer(serializers.ModelSerializer):
    verificacao_estoque = serializers.SerializerMethodField()

    class Meta:
        model = ItemPedido
        fields = (
            "id_item_pedido",
            "produto",
            "receita",
            "quantidade",
            "preco_unitario",
            "custo_unitario",
            "recheio",
            "quantidade_peso",
            "decoracao",
            "verificacao_estoque",
        )
        read_only_fields = ("id_item_pedido", "verificacao_estoque")

<<<<<<< HEAD
    # Confere o saldo do produto pronto e sinaliza quando o item precisa de Produção.
=======
    # RN02: ao registrar ou consultar um pedido externo, verifica imediatamente
    # se há produto pronto suficiente; a falta de saldo direciona o item à Produção.
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
    def get_verificacao_estoque(self, item):
        pedido_serializer = self.parent.parent
        pedido = pedido_serializer.instance
        if (
            pedido is None
            or pedido.tipo != Pedido.Tipo.EXTERNO
            or pedido.subtipo not in (
                Pedido.Subtipo.VITRINE,
                Pedido.Subtipo.PERSONALIZADO,
            )
        ):
            return None

        if item.produto_id is None:
            # O schema não modela bases preparadas como massas ou recheios no
            # Estoque; itens personalizados sem produto de estoque seguem à Produção.
            return {
                "verificado": False,
                "disponivel": False,
                "encaminhar_para_producao": True,
                "motivo": "O item não possui produto pronto associado ao estoque.",
            }

        quantidade = item.quantidade or item.quantidade_peso
        if quantidade is None:
            return {
                "verificado": False,
                "disponivel": None,
                "encaminhar_para_producao": None,
                "motivo": "Informe a quantidade para verificar o estoque.",
            }

        return {
            "verificado": True,
            **Estoque.objects.verificar_disponibilidade(item.produto_id, quantidade),
        }

<<<<<<< HEAD
    # Garante que o item tenha produto ou receita e quantidades válidas.
=======
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
    def validate(self, attrs):
        produto = attrs.get("produto")
        receita = attrs.get("receita")

        if (produto is None) == (receita is None):
            raise serializers.ValidationError(
                "Informe exatamente um: produto ou receita."
            )

        quantidade = attrs.get("quantidade")
        if quantidade is not None and quantidade <= 0:
            raise serializers.ValidationError(
                {"quantidade": "A quantidade deve ser maior que zero."}
            )

        peso = attrs.get("quantidade_peso")
        if peso is not None and peso <= 0:
            raise serializers.ValidationError(
                {"quantidade_peso": "O peso deve ser maior que zero."}
            )
<<<<<<< HEAD
        if quantidade is None and peso is None:
            raise serializers.ValidationError(
                "Informe quantidade ou quantidade_peso para o item."
            )
=======
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8

        preco = attrs.get("preco_unitario")
        if preco is not None and preco < 0:
            raise serializers.ValidationError(
                {"preco_unitario": "O preço não pode ser negativo."}
            )

        custo = attrs.get("custo_unitario")
        if custo is not None and custo < 0:
            raise serializers.ValidationError(
                {"custo_unitario": "O custo não pode ser negativo."}
            )

        return attrs


<<<<<<< HEAD
# Valida e grava pedidos com seus itens, contato e análise operacional integrada.
class PedidoSerializer(serializers.ModelSerializer):
    itens = ItemPedidoSerializer(many=True, required=False)
    contato_nome = serializers.CharField(write_only=True, required=False, allow_blank=False, max_length=100)
    contato_telefone = serializers.CharField(write_only=True, required=False, allow_blank=False, max_length=20)
    analise = serializers.SerializerMethodField()
=======
class PedidoSerializer(serializers.ModelSerializer):
    itens = ItemPedidoSerializer(many=True, required=False)
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8

    class Meta:
        model = Pedido
        fields = (
            "id_pedido",
            "cliente",
            "tipo",
            "subtipo",
            "status",
            "data_entrega",
            "horario_entrega",
            "valor_total",
            "valor_sinal",
            "endereco_entrega",
            "forma_pagamento",
            "itens",
<<<<<<< HEAD
            "analise",
            "contato_nome",
            "contato_telefone",
        )
        read_only_fields = ("id_pedido", "status", "analise")

    # Aplica as regras de tipo, contato, subtipo, itens e valores do pedido.
    def validate(self, attrs):
        pedido_existente = self.instance

        # Pedidos concluídos ou cancelados precisam manter o histórico intacto.
        if pedido_existente and status_operacional(pedido_existente.status) in (
            Pedido.Status.CONCLUIDO,
            Pedido.Status.CANCELADO,
        ):
            raise serializers.ValidationError(
                {"status": "Pedidos concluídos ou cancelados não podem ser editados."}
            )

=======
        )
        read_only_fields = ("id_pedido",)

    def validate(self, attrs):
        pedido_existente = self.instance

>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
        tipo = attrs.get(
            "tipo",
            pedido_existente.tipo if pedido_existente else None,
        )
        subtipo = attrs.get(
            "subtipo",
            pedido_existente.subtipo if pedido_existente else None,
        )
        cliente = attrs.get(
            "cliente",
            pedido_existente.cliente if pedido_existente else None,
        )

<<<<<<< HEAD
        contato_nome = attrs.get("contato_nome")
        contato_telefone = attrs.get("contato_telefone")

        if tipo == Pedido.Tipo.EXTERNO:
            if cliente is None and not (contato_nome and contato_telefone):
                raise serializers.ValidationError(
                    {"cliente": "Informe um cliente ou nome e telefone de contato."}
=======
        if tipo == Pedido.Tipo.EXTERNO:
            if cliente is None:
                raise serializers.ValidationError(
                    {"cliente": "Pedidos externos precisam de um cliente."}
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
                )
            if not subtipo:
                raise serializers.ValidationError(
                    {"subtipo": "Pedidos externos precisam de um subtipo."}
                )
        elif tipo == Pedido.Tipo.INTERNO and subtipo:
            raise serializers.ValidationError(
                {"subtipo": "Pedidos internos não devem ter subtipo."}
            )

        if pedido_existente is None and not attrs.get("itens"):
            raise serializers.ValidationError(
                {"itens": "Informe ao menos um item no pedido."}
            )

        # pedidos de vitrine devem referenciar produtos prontos e itens sem produto pronto nao podem ser incluidos
        itens = attrs.get("itens")
        if (
            tipo == Pedido.Tipo.EXTERNO
            and subtipo == Pedido.Subtipo.VITRINE
            and itens is not None
            and any(item.get("produto") is None for item in itens)
        ):
            raise serializers.ValidationError(
                {"itens": "Pedidos de vitrine devem referenciar produtos prontos."}
            )

        if "itens" in attrs and not attrs["itens"]:
            raise serializers.ValidationError(
                {"itens": "O pedido precisa ter ao menos um item."}
            )

        valor_total = attrs.get(
            "valor_total",
            pedido_existente.valor_total
            if pedido_existente
            else Decimal("0.00"),
        )
        valor_sinal = attrs.get(
            "valor_sinal",
            pedido_existente.valor_sinal
            if pedido_existente
            else Decimal("0.00"),
        )

        if valor_total < 0:
            raise serializers.ValidationError(
                {"valor_total": "O valor total não pode ser negativo."}
            )
        if valor_sinal < 0 or valor_sinal > valor_total:
            raise serializers.ValidationError(
                {"valor_sinal": "O sinal deve estar entre zero e o total."}
            )

        if tipo == Pedido.Tipo.EXTERNO:
            metade = (valor_total / Decimal("2")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            if valor_sinal not in (Decimal("0.00"), metade):
                raise serializers.ValidationError(
                    {"valor_sinal": "O sinal deve ser zero ou metade do total."}
                )

        return attrs

<<<<<<< HEAD
    # Reúne disponibilidade, receitas aplicáveis e faltas no Inventário.
    def get_analise(self, pedido):
        return analisar_pedido(pedido)

    # Cria o pedido e seus itens dentro de uma única transação.
    @transaction.atomic
    def create(self, validated_data):
        nome = validated_data.pop("contato_nome", None)
        telefone = validated_data.pop("contato_telefone", None)
        if not validated_data.get("cliente") and nome and telefone:
            validated_data["cliente"] = Cliente.objects.create(nome=nome, telefone=telefone)
=======
    @transaction.atomic
    def create(self, validated_data):
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
        itens_data = validated_data.pop("itens", [])
        pedido = Pedido.objects.create(**validated_data)

        for item_data in itens_data:
            ItemPedido.objects.create(pedido=pedido, **item_data)

        return pedido

<<<<<<< HEAD
    # Atualiza os dados do pedido e substitui itens somente quando enviados.
    @transaction.atomic
    def update(self, instance, validated_data):
        nome = validated_data.pop("contato_nome", None)
        telefone = validated_data.pop("contato_telefone", None)
        if not validated_data.get("cliente") and nome and telefone:
            validated_data["cliente"] = Cliente.objects.create(nome=nome, telefone=telefone)
=======
    @transaction.atomic
    def update(self, instance, validated_data):
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
        itens_data = validated_data.pop("itens", None)

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()

        if itens_data is not None:
            instance.itens.all().delete()
            for item_data in itens_data:
                ItemPedido.objects.create(pedido=instance, **item_data)

        return instance
<<<<<<< HEAD

    # Exibe status operacionais atuais mesmo para registros com valores antigos.
    def to_representation(self, instance):
        dados = super().to_representation(instance)
        dados["status"] = status_operacional(instance.status)
        return dados
=======
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
