from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

# Soma lotes dentro da validade e indica se a quantidade atende ao pedido.
class EstoqueManager(models.Manager):
    def verificar_disponibilidade(self, produto_id, quantidade):
        hoje = timezone.localdate()
        saldo = (
            self.filter(produto_id=produto_id)
            .filter(Q(data_validade__isnull=True) | Q(data_validade__gte=hoje))
            .aggregate(total=Sum("quantidade_disponivel"))["total"]
            or Decimal("0.00")
        )
        disponivel = saldo >= quantidade

        return {
            "quantidade_solicitada": quantidade,
            "quantidade_disponivel": saldo,
            "disponivel": disponivel,
            "encaminhar_para_producao": not disponivel,
        }

# Representa um lote de produto pronto com quantidade, validade e custo.
class Estoque(models.Model):
    id_estoque = models.AutoField(primary_key=True)
    produto = models.ForeignKey(
        "pedido.Produto",
        on_delete=models.PROTECT,
        db_column="id_produto",
        related_name="lotes_estoque",
    )

    quantidade_disponivel = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    data_validade = models.DateField(null=True, blank=True)
    custo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    objects = EstoqueManager()

    class Meta:
        db_table = "estoque"
        managed = False
