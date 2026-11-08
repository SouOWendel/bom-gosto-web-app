from django.db import migrations, models


def create_ingrediente_receita(apps, schema_editor):
    model = apps.get_model("producao", "IngredienteReceita")
    with schema_editor.connection.cursor() as cursor:
        tables = schema_editor.connection.introspection.table_names(cursor)
    if model._meta.db_table not in tables:
        schema_editor.create_model(model)


def ensure_ingrediente_receita_unique(apps, schema_editor):
    model = apps.get_model("producao", "IngredienteReceita")
    field_columns = tuple(
        model._meta.get_field(field_name).column
        for field_name in ("ingrediente", "receita")
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
        fields=("ingrediente", "receita"),
        name="uq_ingrediente_receita",
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
        ("inventario", "0002_create_ingrediente_table"),
        ("pedido", "0003_create_cancelamento_receita_produto"),
        ("producao", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="ingredientereceita",
            options={"db_table": "ingrediente_receita"},
        ),
        migrations.RunPython(create_ingrediente_receita),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_ingrediente_receita_unique),
            ],
            state_operations=[
                migrations.AddConstraint(
                    model_name="ingredientereceita",
                    constraint=models.UniqueConstraint(
                        fields=("ingrediente", "receita"),
                        name="uq_ingrediente_receita",
                    ),
                ),
            ],
        ),
    ]
