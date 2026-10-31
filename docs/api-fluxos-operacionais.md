# Contratos da API operacional

As rotas abaixo usam a base `/api`, exigem sessão autenticada e senha inicial já alterada, exceto autenticação. Quantidades e valores monetários são decimais enviados como texto. Erros de validação retornam `400` com os campos que precisam de ajuste; recursos inexistentes retornam `404`; falta de autenticação retorna `401` e primeiro acesso pendente retorna `403`.

## Pedidos

`GET /pedido/`, `GET /pedido/{id}/`, `POST /pedido/`, `PUT /pedido/{id}/` e `PATCH /pedido/{id}/` consultam, criam e editam pedidos. `DELETE` não é disponibilizado. Todo pedido inicia em `pedido_feito`; os status operacionais são `pedido_feito`, `em_producao`, `producao_concluida`, `concluido` e `cancelado`.

Pedido externo requer `subtipo` (`vitrine` ou `personalizado`) e `cliente` ou os campos `contato_nome` e `contato_telefone`. Quando informados sem cliente, os dados criam um registro na tabela Cliente existente. Pedido interno não exige cliente nem subtipo. Pedido novo e resposta após edição incluem `analise`, com saldos do Estoque, receitas sugeridas, ausências e ingredientes insuficientes. Falta de saldo ou receita não impede salvar o pedido.

Exemplo de criação:

```json
{
  "tipo": "externo",
  "subtipo": "personalizado",
  "contato_nome": "Ana",
  "contato_telefone": "11999990000",
  "valor_total": "80.00",
  "valor_sinal": "40.00",
  "itens": [{"produto": 1, "quantidade": 1, "preco_unitario": "80.00"}]
}
```

`POST /pedido/{id}/consumir-estoque/` confirma que os produtos prontos foram consumidos. Baixa os lotes válidos por validade e marca o pedido como `concluido`. Repetir a confirmação retorna `400` sem movimentar novamente.

Para reposição interna, `POST /pedido/{id}/concluir/` muda `producao_concluida` para `concluido` sem baixar novamente os lotes que a produção acabou de gerar.

`POST /pedido/{id}/cancelar/` exige `consumos` com `ingrediente_id` e `quantidade` (zero é aceito) e `destino` como `descarte` ou `estoque`. Para reaproveitar em estoque, envie também:

```json
{
  "consumos": [{"ingrediente_id": 1, "quantidade": "0.50"}],
  "destino": "estoque",
  "produto_aproveitado": {
    "nome": "Bolo de teste",
    "quantidade": "1.00",
    "data_validade": "2026-11-05",
    "preco_venda": "45.00",
    "custo": "18.30"
  }
}
```

Um segundo cancelamento do mesmo pedido retorna `400`. O schema atual guarda destino e data em Cancelamento, mas não tem colunas para armazenar o detalhamento dos consumos informados.
Se o status já for `producao_concluida`, ingredientes não são baixados novamente e um lote de reaproveitamento não é duplicado. O destino `descarte` é recusado nesse ponto porque o schema não relaciona o lote produzido ao pedido e não permite identificar com segurança qual saldo remover.

`GET /cancelamento/` e `GET /cancelamento/{id}/` consultam os registros de cancelamento gravados na tabela existente.

## Receitas e produção

- `GET/POST /producao/receitas/` e `GET/PUT/PATCH/DELETE /producao/receitas/{id}/`: CRUD de Receita com `rendimento_quantidade`, ingredientes (`ingredientes`: ingrediente e quantidade necessária) e produtos relacionados (`produtos_relacionados`: produto, quantidade, unidade de medida e custo unitário opcional). Receita vinculada a item de pedido não pode ser excluída (`400`).
- `POST /producao/pedidos/{id}/validar/`: valida receitas, componentes e saldos sem movimentar dados.
- `POST /producao/pedidos/{id}/iniciar/`: muda `pedido_feito` para `em_producao`, sem baixa ou entrada.
- `POST /producao/pedidos/{id}/concluir/`: exige `data_validade` e a lista real `consumos`; quantidades zero são permitidas. Calcula custo pelos custos atuais, baixa Inventário, cria lote apenas para o saldo que falta e muda o status para `producao_concluida` na mesma transação.

Exemplo de conclusão:

```json
{
  "data_validade": "2026-11-05",
  "consumos": [
    {"ingrediente_id": 1, "quantidade": "0.80"},
    {"ingrediente_id": 2, "quantidade": "0.00"}
  ]
}
```

Não é possível concluir pedido que não esteja em produção, sem ingredientes confirmados, com saldo insuficiente ou sem produto associado à receita. Uma conclusão repetida retorna `400`.

## Estoque e Inventário

Estoque oferece `GET /estoque/`, consulta de detalhe, `PUT/PATCH` e `GET /estoque/disponibilidade/`. Cadastro manual (`POST`) e exclusão (`DELETE`) não estão habilitados; novos lotes vêm da conclusão da Produção ou do cancelamento reaproveitado.

Inventário oferece `GET/POST /inventario/ingrediente/` e `GET/PUT/PATCH /inventario/ingrediente/{id}/`. Respostas incluem `data_validade`, `abaixo_do_minimo` e `alerta_validade`. Estoque e Inventário classificam validade como `critico` (vencido ou vence hoje), `atencao` (até sete dias) ou `preventivo` (até quinze dias); validade mais distante ou ausente retorna alerta nulo.

## Conta inicial

Para criar a conta inicial de forma administrativa, use `python manage.py criar_usuario_inicial <login>` dentro do backend. Uma senha provisória aleatória é exibida uma única vez e o primeiro acesso exige troca. `POST /auth/cadastro-teste/` permanece restrito a `DEBUG=True` para testes locais.
