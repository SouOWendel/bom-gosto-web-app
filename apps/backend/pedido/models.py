from django.db import models


class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)
    endereco = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = "cliente"
        managed = False


class Receita(models.Model):
    id_receita = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    rendimento_quantidade = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    custo_calculado = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    class Meta:
        db_table = "receita"
        managed = False


class Produto(models.Model):
    id_produto = models.AutoField(primary_key=True)
    receita = models.ForeignKey(
        Receita,
        on_delete=models.SET_NULL,
        db_column="receita_id",
        null=True,
        blank=True,
        related_name="produtos",
    )
    nome = models.CharField(max_length=100)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "produto"
        managed = False


class Pedido(models.Model):
    class Tipo(models.TextChoices):
        INTERNO = "interno", "Interno"
        EXTERNO = "externo", "Externo"

    class Subtipo(models.TextChoices):
        VITRINE = "vitrine", "Vitrine"
        PERSONALIZADO = "personalizado", "Personalizado"

    class Status(models.TextChoices):
        PEDIDO_FEITO = "pedido_feito", "Pedido feito"
        PAGAMENTO_PARCIAL = "pagamento_parcial", "Pagamento parcial"
        EM_PRODUCAO = "pedido_em_producao", "Em produção"
        PAGAMENTO_TOTAL = "pagamento_total", "Pagamento total"
        CONCLUIDO = "pedido_concluido", "Concluído"
        CANCELADO = "pedido_cancelado", "Cancelado"

    id_pedido = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        db_column="cliente_id",
        null=True,
        blank=True,
        related_name="pedidos",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    subtipo = models.CharField(
        max_length=20, choices=Subtipo.choices, null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PEDIDO_FEITO,
    )
    data_entrega = models.DateField(null=True, blank=True)
    horario_entrega = models.TimeField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_sinal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    endereco_entrega = models.CharField(max_length=200, null=True, blank=True)
    forma_pagamento = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
        db_table = "pedido"
        managed = False


class ItemPedido(models.Model):
    id_item_pedido = models.AutoField(primary_key=True)
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        db_column="pedido_id",
        related_name="itens",
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        db_column="produto_id",
        null=True,
        blank=True,
        related_name="itens_pedido",
    )
    receita = models.ForeignKey(
        Receita,
        on_delete=models.PROTECT,
        db_column="receita_id",
        null=True,
        blank=True,
        related_name="itens_pedido",
    )
    quantidade = models.IntegerField(null=True, blank=True)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    custo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    recheio = models.CharField(max_length=100, null=True, blank=True)
    quantidade_peso = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    decoracao = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = "item_pedido"
        managed = False


