from django.db import migrations


FOREIGN_KEYS = (
    ("produto", "receita_id", "receita", "id_receita", "SET NULL", "fk_produto_receita_set_null"),
    ("pedido", "cliente_id", "cliente", "id_cliente", "RESTRICT", "fk_pedido_cliente_restrict"),
    ("item_pedido", "pedido_id", "pedido", "id_pedido", "CASCADE", "fk_item_pedido_pedido_cascade"),
    ("item_pedido", "produto_id", "produto", "id_produto", "RESTRICT", "fk_item_pedido_produto_restrict"),
    ("item_pedido", "receita_id", "receita", "id_receita", "RESTRICT", "fk_item_pedido_receita_restrict"),
    ("receita_produto", "id_receita", "receita", "id_receita", "CASCADE", "fk_receita_produto_receita_cascade"),
    ("receita_produto", "id_produto", "produto", "id_produto", "CASCADE", "fk_receita_produto_produto_cascade"),
    ("ingrediente_receita", "receita_id", "receita", "id_receita", "CASCADE", "fk_ingrediente_receita_receita_cascade"),
)

DELETE_ACTION_CODES = {
    "CASCADE": "c",
    "NO ACTION": "a",
    "RESTRICT": "r",
    "SET NULL": "n",
}


def set_delete_actions(schema_editor, default_action=False):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        for table, column, ref_table, ref_column, action, constraint_name in FOREIGN_KEYS:
            cursor.execute(
                """
                SELECT fk.conname, fk.confdeltype
                FROM pg_constraint AS fk
                JOIN pg_attribute AS source_column
                    ON source_column.attrelid = fk.conrelid
                    AND source_column.attnum = fk.conkey[1]
                JOIN pg_attribute AS target_column
                    ON target_column.attrelid = fk.confrelid
                    AND target_column.attnum = fk.confkey[1]
                WHERE fk.contype = 'f'
                    AND fk.conrelid = %s::regclass
                    AND fk.confrelid = %s::regclass
                    AND array_length(fk.conkey, 1) = 1
                    AND source_column.attname = %s
                    AND target_column.attname = %s
                """,
                [table, ref_table, column, ref_column],
            )
            constraints = cursor.fetchall()
            wanted_action = "NO ACTION" if default_action else action
            wanted_code = DELETE_ACTION_CODES[wanted_action]

            if len(constraints) == 1 and constraints[0][1] == wanted_code:
                continue

            quoted_table = schema_editor.quote_name(table)
            for existing_name, _ in constraints:
                cursor.execute(
                    "ALTER TABLE {} DROP CONSTRAINT {}".format(
                        quoted_table,
                        schema_editor.quote_name(existing_name),
                    )
                )

            cursor.execute(
                "ALTER TABLE {} ADD CONSTRAINT {} FOREIGN KEY ({}) "
                "REFERENCES {} ({}) ON DELETE {}".format(
                    quoted_table,
                    schema_editor.quote_name(constraint_name),
                    schema_editor.quote_name(column),
                    schema_editor.quote_name(ref_table),
                    schema_editor.quote_name(ref_column),
                    wanted_action,
                )
            )


def apply_delete_actions(apps, schema_editor):
    set_delete_actions(schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("estoque", "0001_create_estoque_table"),
        ("producao", "0002_create_ingrediente_receita_table"),
    ]

    operations = [
        migrations.RunPython(apply_delete_actions),
    ]
