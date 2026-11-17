from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from estoque.models import Estoque

from .models import (
    Cancelamento,
    Cliente,
    ItemPedido,
    Pedido,
    Produto,
    ReceitaProduto,
    status_operacional,
)


# Reaproveita o cliente com o mesmo telefone em vez de duplicar o cadastro e guarda
# no cliente o endereço de entrega mais recente.
def _cliente_por_contato(nome, telefone, endereco=None):
    cliente = Cliente.objects.filter(telefone=telefone).order_by("id_cliente").first()
    if cliente is None:
        return Cliente.objects.create(nome=nome, telefone=telefone, endereco=endereco)
    campos = []
    if cliente.nome != nome:
        cliente.nome = nome
        campos.append("nome")
    # Pedido sem endereço é retirada: mantém o último endereço conhecido do cliente.
    if endereco and cliente.endereco != endereco:
        cliente.endereco = endereco
        campos.append("endereco")
    if campos:
        cliente.save(update_fields=campos)
    return cliente


# Receita complementar do produto (Receita_Produto, RF18): a quantidade usa a mesma
# unidade do rendimento da receita e vale para cada unidade do produto.
class ReceitaComplementarSerializer(serializers.ModelSerializer):
    receita_nome = serializers.CharField(source="receita.nome", read_only=True)

    class Meta:
        model = ReceitaProduto
        fields = ("receita", "receita_nome", "quantidade", "unidade_medida")

    def validate_quantidade(self, valor):
        if valor <= 0:
            raise serializers.ValidationError("A quantidade da receita deve ser maior que zero.")
        return valor


# Serializador para consulta e cadastro de produtos comercializados.
class ProdutoSerializer(serializers.ModelSerializer):
    receita_nome = serializers.CharField(source="receita.nome", read_only=True, allow_null=True)
    receitas_complementares = ReceitaComplementarSerializer(
        many=True, required=False, source="receitaproduto_set"
    )
    # Saldo pronto dentro da validade, exibido ao montar o pedido (RN05).
    saldo_disponivel = serializers.SerializerMethodField()

    class Meta:
        model = Produto
        fields = ("id_produto", "nome", "preco_venda", "receita", "receita_nome", "receitas_complementares", "saldo_disponivel")
        read_only_fields = ("id_produto", "receita_nome")

    # A listagem já traz o saldo anotado; criação e edição calculam pelo mesmo critério.
    def get_saldo_disponivel(self, produto):
        saldo = getattr(produto, "saldo_valido", None)
        if saldo is None:
            saldo = Estoque.objects.verificar_disponibilidade(produto.pk, Decimal("0"))["quantidade_disponivel"]
        return str(saldo or Decimal("0.00"))

    def validate_preco_venda(self, valor):
        if valor < 0:
            raise serializers.ValidationError("O preço de venda não pode ser negativo.")
        return valor

    # A principal fica em Produto.receita; as complementares não podem repeti-la nem se repetir.
    def validate(self, attrs):
        complementares = attrs.get("receitaproduto_set")
        if complementares is None:
            return attrs
        principal = attrs.get("receita", self.instance.receita if self.instance else None)
        ids = [linha["receita"].pk for linha in complementares]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                {"receitas_complementares": "Cada receita pode aparecer uma vez no produto."}
            )
        if principal is not None and principal.pk in ids:
            raise serializers.ValidationError(
                {"receitas_complementares": "A receita principal não pode ser repetida como complementar."}
            )
        return attrs

    def _gravar_complementares(self, produto, complementares):
        ReceitaProduto.objects.filter(produto=produto).delete()
        for linha in complementares:
            ReceitaProduto.objects.create(produto=produto, **linha)

    @transaction.atomic
    def create(self, validated_data):
        complementares = validated_data.pop("receitaproduto_set", [])
        produto = Produto.objects.create(**validated_data)
        self._gravar_complementares(produto, complementares)
        return produto

    # Substitui as complementares somente quando a lista é enviada.
    @transaction.atomic
    def update(self, instance, validated_data):
        complementares = validated_data.pop("receitaproduto_set", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if complementares is not None:
            self._gravar_complementares(instance, complementares)
        return instance


# Devolve os dados do registro de cancelamento para consulta pela API.
class CancelamentoRegistroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cancelamento
        fields = ("id_cancelamento", "pedido", "destino", "data_cancelamento")
        read_only_fields = fields


# Valida os dados de cada item e apresenta sua disponibilidade em Estoque.
class ItemPedidoSerializer(serializers.ModelSerializer):
    verificacao_estoque = serializers.SerializerMethodField()
    produto_nome = serializers.CharField(source="produto.nome", read_only=True, default=None)
    receita_nome = serializers.CharField(source="receita.nome", read_only=True, default=None)

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
            "produto_nome",
            "receita_nome",
        )
        read_only_fields = ("id_item_pedido", "verificacao_estoque", "produto_nome", "receita_nome")

    # Confere o saldo do produto pronto e sinaliza quando o item precisa de Produção.
    def get_verificacao_estoque(self, item):
        pedido = item.pedido
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

    # Itens novos sempre apontam para um produto do catálogo; as receitas usadas na
    # produção vêm do próprio produto. A coluna receita fica só para pedidos antigos.
    def validate(self, attrs):
        if attrs.get("receita") is not None:
            raise serializers.ValidationError(
                {"receita": "Escolha um produto do catálogo; a receita vem do cadastro do produto."}
            )
        if attrs.get("produto") is None:
            raise serializers.ValidationError({"produto": "Informe o produto do item."})

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
        if quantidade is None and peso is None:
            raise serializers.ValidationError(
                "Informe quantidade ou quantidade_peso para o item."
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


# Valida e grava pedidos com seus itens e contato.
# A análise de produção fica em /producao/pedidos/<id>/validar/: calculá-la aqui
# pesava cada listagem e, se falhasse, devolvia erro com o pedido já gravado.
class PedidoSerializer(serializers.ModelSerializer):
    itens = ItemPedidoSerializer(many=True, required=False)
    contato_nome = serializers.CharField(write_only=True, required=False, allow_blank=False, max_length=100)
    contato_telefone = serializers.CharField(write_only=True, required=False, allow_blank=False, max_length=20)
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True, default=None)
    cliente_telefone = serializers.CharField(source="cliente.telefone", read_only=True, default=None)

    class Meta:
        model = Pedido
        fields = (
            "id_pedido",
            "cliente",
            "cliente_nome",
            "cliente_telefone",
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
            "contato_nome",
            "contato_telefone",
        )
        read_only_fields = ("id_pedido", "status", "cliente_nome", "cliente_telefone")

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

        # Pedidos antigos com item de receita ficam só para leitura: o formato atual
        # exige produto em todos os itens e não há como convertê-los sem perder dados.
        if pedido_existente and pedido_existente.itens.filter(receita__isnull=False).exists():
            raise serializers.ValidationError(
                {"itens": "Pedidos antigos com item de receita não podem ser editados; cancele e cadastre um novo, se necessário."}
            )

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

        contato_nome = attrs.get("contato_nome")
        contato_telefone = attrs.get("contato_telefone")

        if tipo == Pedido.Tipo.EXTERNO:
            if cliente is None and not (contato_nome and contato_telefone):
                raise serializers.ValidationError(
                    {"cliente": "Informe um cliente ou nome e telefone de contato."}
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

        # Vitrine vende só o que já está pronto: a soma pedida de cada produto precisa
        # caber no saldo válido do Estoque, sem encaminhar nada para a Produção.
        if tipo == Pedido.Tipo.EXTERNO and subtipo == Pedido.Subtipo.VITRINE:
            self._validar_estoque_da_vitrine(itens, pedido_existente)

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
        # O sinal é livre: zero (sem sinal) ou um valor positivo menor que o total.
        if valor_sinal < 0 or (valor_sinal > 0 and valor_sinal >= valor_total):
            raise serializers.ValidationError(
                {"valor_sinal": "O sinal deve ser zero ou um valor positivo menor que o total."}
            )

        return attrs

    # Soma o pedido por produto (quantidade ou peso, como em _quantidade_item da Produção)
    # e recusa o pedido de vitrine quando algum produto não tem saldo suficiente.
    def _validar_estoque_da_vitrine(self, itens, pedido_existente):
        if itens is None:
            if pedido_existente is None:
                return
            itens = [
                {
                    "produto": item.produto,
                    "quantidade": item.quantidade,
                    "quantidade_peso": item.quantidade_peso,
                }
                for item in pedido_existente.itens.select_related("produto")
            ]

        pedido_por_produto = {}
        for item in itens:
            produto = item.get("produto")
            if produto is None:
                continue
            quantidade = Decimal(item.get("quantidade") or item.get("quantidade_peso") or 0)
            pedido_por_produto[produto] = pedido_por_produto.get(produto, Decimal("0")) + quantidade

        sem_saldo = []
        for produto, quantidade in pedido_por_produto.items():
            saldo = Estoque.objects.verificar_disponibilidade(produto.pk, quantidade)[
                "quantidade_disponivel"
            ]
            if quantidade > saldo:
                saldo_texto = f"{saldo.normalize():f}".replace(".", ",")
                sem_saldo.append(f"{produto.nome} (há {saldo_texto} em estoque)")

        if sem_saldo:
            raise serializers.ValidationError(
                {"itens": "Pedido de vitrine só usa o que há em estoque. Sem saldo suficiente: " + ", ".join(sem_saldo) + "."}
            )

    # Cria o pedido e seus itens dentro de uma única transação.
    @transaction.atomic
    def create(self, validated_data):
        nome = validated_data.pop("contato_nome", None)
        telefone = validated_data.pop("contato_telefone", None)
        if not validated_data.get("cliente") and nome and telefone:
            validated_data["cliente"] = _cliente_por_contato(
                nome, telefone, validated_data.get("endereco_entrega")
            )
        itens_data = validated_data.pop("itens", [])
        pedido = Pedido.objects.create(**validated_data)

        for item_data in itens_data:
            ItemPedido.objects.create(pedido=pedido, **item_data)

        return pedido

    # Atualiza os dados do pedido e substitui itens somente quando enviados.
    @transaction.atomic
    def update(self, instance, validated_data):
        nome = validated_data.pop("contato_nome", None)
        telefone = validated_data.pop("contato_telefone", None)
        if not validated_data.get("cliente") and nome and telefone:
            validated_data["cliente"] = _cliente_por_contato(
                nome,
                telefone,
                validated_data.get("endereco_entrega", instance.endereco_entrega),
            )
        # Reposição interna não tem cliente (RN18): ao virar interno, solta o vínculo.
        if validated_data.get("tipo", instance.tipo) == Pedido.Tipo.INTERNO:
            validated_data["cliente"] = None
        itens_data = validated_data.pop("itens", None)

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()

        if itens_data is not None:
            instance.itens.all().delete()
            for item_data in itens_data:
                ItemPedido.objects.create(pedido=instance, **item_data)

        return instance

    # Exibe status operacionais atuais mesmo para registros com valores antigos.
    def to_representation(self, instance):
        dados = super().to_representation(instance)
        dados["status"] = status_operacional(instance.status)
        return dados
