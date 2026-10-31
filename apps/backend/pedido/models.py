from django.db import models


# Converte status legados para a etapa operacional equivalente ao ler pedidos antigos.
def status_operacional(status):
    """Traduz status antigos em leitura, sem exigir alteração nos dados existentes."""
    return {
        "pagamento_parcial": "em_producao",
        "pagamento_total": "pedido_feito",
        "pedido_em_producao": "em_producao",
        "pedido_concluido": "concluido",
        "pedido_cancelado": "cancelado",
    }.get(status, status)

# models do fluxo de pedidos
# migrations do Django criam e atualizam suas tabelas
# `on_delete` define o comportamento ao excluir objetos pelo ORM
# comandos SQL diretos seguem as regras de chave estrangeira definidas no banco
# `CASCADE` propaga a exclusao pelo ORM
# `PROTECT` impede excluir um objeto relacionado
# `SET_NULL` limpa uma FK anulavel
# Guarda nome e contato usados pelos pedidos externos.
class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)
    endereco = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = "cliente"


# Registra o rendimento e o custo de referência de cada receita.
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


# Representa um produto vendável e sua receita principal, quando houver.
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


# Centraliza dados comerciais, entrega e status operacional do pedido.
class Pedido(models.Model):
    # choices centraliza valores aceitos pela aplicacao (nao cria constraints `CHECK` no banco)
    class Tipo(models.TextChoices):
        INTERNO = "interno", "Interno"
        EXTERNO = "externo", "Externo"

    class Subtipo(models.TextChoices):
        VITRINE = "vitrine", "Vitrine"
        PERSONALIZADO = "personalizado", "Personalizado"

    class Status(models.TextChoices):
        PEDIDO_FEITO = "pedido_feito", "Pedido feito"
        EM_PRODUCAO = "em_producao", "Em produção"
        PRODUCAO_CONCLUIDA = "producao_concluida", "Produção concluída"
        CONCLUIDO = "concluido", "Concluído"
        CANCELADO = "cancelado", "Cancelado"

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


# Guarda cada produto ou receita, quantidade e especificações incluídas no pedido.
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


# Mapeia relações complementares entre receitas e produtos existentes no schema.
class ReceitaProduto(models.Model):
    id_receita_produto = models.AutoField(primary_key=True)
    receita = models.ForeignKey(Receita, on_delete=models.CASCADE, db_column="id_receita")
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, db_column="id_produto")
    quantidade = models.DecimalField(max_digits=10, decimal_places=3)
    unidade_medida = models.CharField(max_length=20, null=True, blank=True)
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "receita_produto"
        managed = False


# Registra o pedido cancelado, a data e o destino informado para o resultado.
class Cancelamento(models.Model):
    id_cancelamento = models.AutoField(primary_key=True)
    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, db_column="pedido_id")
    destino = models.CharField(max_length=20, null=True, blank=True)
    data_cancelamento = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "cancelamento"
        managed = False
