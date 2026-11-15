from django.db import migrations, models


def create_tables(apps, schema_editor):
    for model_name in ("Cancelamento", "ReceitaProduto"):
        model = apps.get_model("pedido", model_name)
        with schema_editor.connection.cursor() as cursor:
            tables = schema_editor.connection.introspection.table_names(cursor)
        if model._meta.db_table not in tables:
            schema_editor.create_model(model)


def ensure_receita_produto_unique(apps, schema_editor):
    model = apps.get_model("pedido", "ReceitaProduto")
    field_columns = tuple(
        model._meta.get_field(field_name).column
        for field_name in ("receita", "produto")
    )
    columns = set(field_columns)
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(
            cursor,
            model._meta.db_table,
        )
    if any(
        constraint.get("unique")
        and set(constraint.get("columns") or ()) == columns
        for constraint in constraints.values()
    ):
        return
    constraint = models.UniqueConstraint(
        fields=("receita", "produto"),
        name="uq_receita_produto",
    )
    if schema_editor.connection.vendor == "sqlite":
        schema_editor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS {} ON {} ({}, {})".format(
                schema_editor.quote_name(constraint.name),
                schema_editor.quote_name(model._meta.db_table),
                *(schema_editor.quote_name(column) for column in field_columns),
            )
        )
    else:
        schema_editor.add_constraint(model, constraint)


class Migration(migrations.Migration):

    dependencies = [
        ("pedido", "0002_cancelamento_receitaproduto_alter_pedido_status"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="cancelamento",
            options={"db_table": "cancelamento"},
        ),
        migrations.AlterModelOptions(
            name="receitaproduto",
            options={"db_table": "receita_produto"},
        ),
        migrations.RunPython(create_tables),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_receita_produto_unique),
            ],
            state_operations=[
                migrations.AddConstraint(
                    model_name="receitaproduto",
                    constraint=models.UniqueConstraint(
                        fields=("receita", "produto"),
                        name="uq_receita_produto",
                    ),
                ),
            ],
        ),
    ]
