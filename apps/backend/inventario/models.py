from django.db import models


<<<<<<< HEAD
# Mantém saldo, custo, validade e nível mínimo de cada matéria-prima.
=======
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
class Ingrediente(models.Model):
    id_ingrediente = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    quantidade_disponivel = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    custo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    data_validade = models.DateField(null=True, blank=True)
    quantidade_minima = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        db_table = "ingrediente"
        managed = False
