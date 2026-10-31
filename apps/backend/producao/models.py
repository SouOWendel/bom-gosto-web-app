from django.db import models


# Relaciona cada receita aos ingredientes e às quantidades da composição.
class IngredienteReceita(models.Model):
    id_ingrediente_receita = models.AutoField(primary_key=True)
    receita = models.ForeignKey(
        "pedido.Receita",
        on_delete=models.CASCADE,
        db_column="receita_id",
        related_name="composicao",
    )
    ingrediente = models.ForeignKey(
        "inventario.Ingrediente",
        on_delete=models.PROTECT,
        db_column="ingrediente_id",
    )
    quantidade_necessaria = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        db_table = "ingrediente_receita"
        managed = False


