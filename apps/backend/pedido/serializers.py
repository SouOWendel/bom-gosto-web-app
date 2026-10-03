from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from rest_framework import serializers

from .models import ItemPedido, Pedido


class ItemPedidoSerializer(serializers.ModelSerializer):
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
        )
        read_only_fields = ("id_item_pedido",)

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


class PedidoSerializer(serializers.ModelSerializer):
    itens = ItemPedidoSerializer(many=True, required=False)

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
        )
        read_only_fields = ("id_pedido",)

    def validate(self, attrs):
        pedido_existente = self.instance

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

        if tipo == Pedido.Tipo.EXTERNO:
            if cliente is None:
                raise serializers.ValidationError(
                    {"cliente": "Pedidos externos precisam de um cliente."}
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

    @transaction.atomic
    def create(self, validated_data):
        itens_data = validated_data.pop("itens", [])
        pedido = Pedido.objects.create(**validated_data)

        for item_data in itens_data:
            ItemPedido.objects.create(pedido=pedido, **item_data)

        return pedido

    @transaction.atomic
    def update(self, instance, validated_data):
        itens_data = validated_data.pop("itens", None)

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()

        if itens_data is not None:
            instance.itens.all().delete()
            for item_data in itens_data:
                ItemPedido.objects.create(pedido=instance, **item_data)

        return instance


