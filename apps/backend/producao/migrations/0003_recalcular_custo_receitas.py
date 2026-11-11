from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations


# Preenche o custo das receitas criadas antes do cálculo automático ao salvar.
def recalcular(apps, schema_editor):
    Receita = apps.get_model("pedido", "Receita")
    IngredienteReceita = apps.get_model("producao", "IngredienteReceita")
    for receita in Receita.objects.all():
        custo = Decimal("0")
        for linha in IngredienteReceita.objects.filter(receita_id=receita.pk).select_related("ingrediente"):
            custo += linha.quantidade_necessaria * (linha.ingrediente.custo_unitario or Decimal("0"))
        receita.custo_calculado = custo.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        receita.save(update_fields=["custo_calculado"])


class Migration(migrations.Migration):
    dependencies = [
        ("producao", "0002_create_ingrediente_receita_table"),
        ("pedido", "0003_create_cancelamento_receita_produto"),
        ("inventario", "0003_ingrediente_unidade_medida"),
    ]

    operations = [migrations.RunPython(recalcular, migrations.RunPython.noop)]
