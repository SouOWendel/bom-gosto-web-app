from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from pedido.models import Produto


class EstoqueManager(models.Manager):
    # pedidos so podem considerar produtos prontos em lotes sem validade ou com validade ainda vigente. lotes vencidos não compõem o saldo
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


# define a estrutura das tabelas no banco de dados, incluindo os campos e seus tipos de dados, bem como as relacoes entre as tabelas
class Estoque(models.Model):
    id_estoque = models.AutoField(primary_key=True)
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        db_column="id_produto",
        related_name="lotes_estoque",
    )
    quantidade_disponivel = models.DecimalField(max_digits=10, decimal_places=2)
    data_validade = models.DateField(null=True, blank=True)
    custo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    objects = EstoqueManager()

    class Meta:
        db_table = "estoque"
        managed = False
