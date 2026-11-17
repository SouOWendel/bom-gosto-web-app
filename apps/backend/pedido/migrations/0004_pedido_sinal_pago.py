from django.db import migrations, models


# Pedidos que já estão em produção tiveram o sinal recebido pela regra atual.
def marcar_sinal_dos_pedidos_em_producao(apps, schema_editor):
    Pedido = apps.get_model("pedido", "Pedido")
    Pedido.objects.filter(
        status__in=("em_producao", "producao_concluida", "pagamento_parcial", "pedido_em_producao"),
        valor_sinal__gt=0,
    ).update(sinal_pago=True)


class Migration(migrations.Migration):

    dependencies = [
        ("pedido", "0003_create_cancelamento_receita_produto"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedido",
            name="sinal_pago",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(marcar_sinal_dos_pedidos_em_producao, migrations.RunPython.noop),
    ]
