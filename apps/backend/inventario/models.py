from django.db import models

# define a estrutura das tabelas no banco de dados, incluindo os campos e seus tipos de dados, bem como as relações entre as tabelas
class Ingrediente(models.Model):
    id_ingrediente = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    quantidade_disponivel = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    custo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    data_validade = models.DateField(null=True, blank=True)
    quantidade_minima = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "ingrediente"
        managed = False