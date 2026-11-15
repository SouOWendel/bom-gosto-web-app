import django.db.models.deletion
from django.db import migrations, models


def create_estoque_if_missing(apps, schema_editor):
    model = apps.get_model("estoque", "Estoque")
    with schema_editor.connection.cursor() as cursor:
        tables = schema_editor.connection.introspection.table_names(cursor)
    if model._meta.db_table not in tables:
        schema_editor.create_model(model)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("pedido", "0003_create_cancelamento_receita_produto"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Estoque",
                    fields=[
                        (
                            "id_estoque",
                            models.AutoField(primary_key=True, serialize=False),
                        ),
                        (
                            "produto",
                            models.ForeignKey(
                                db_column="id_produto",
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="lotes_estoque",
                                to="pedido.produto",
                            ),
                        ),
                        (
                            "quantidade_disponivel",
                            models.DecimalField(decimal_places=2, max_digits=10),
                        ),
                        ("data_validade", models.DateField(blank=True, null=True)),
                        (
                            "custo",
                            models.DecimalField(
                                blank=True,
                                decimal_places=2,
                                max_digits=10,
                                null=True,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "estoque",
                    },
                ),
            ],
        ),
        migrations.RunPython(create_estoque_if_missing),
    ]
