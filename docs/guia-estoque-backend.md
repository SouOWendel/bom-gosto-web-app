# Guia do back-end de Estoque

O Estoque recebe lotes por dois fluxos automáticos: conclusão de Produção e reaproveitamento no cancelamento de um pedido. A API permite consultar e editar lotes existentes, mas não aceita `POST` para cadastro manual nem `DELETE` para exclusão.

## Endpoints

- `GET /api/estoque/` e `GET /api/estoque/{id}/`: consulta dos lotes e alertas.
- `PUT` ou `PATCH /api/estoque/{id}/`: edição permitida de quantidade, validade e custo.
- `GET /api/estoque/disponibilidade/?id_produto={id}&quantidade={valor}`: soma lotes válidos e informa se a demanda segue para Produção.

Cada lote inclui `vencido` e `alerta_validade`. O nível é `critico` quando está vencido ou vence hoje, `atencao` até sete dias e `preventivo` até quinze dias. Lotes vencidos não são contabilizados na disponibilidade.

## Movimentações pelo fluxo operacional

- Produção: `POST /api/producao/pedidos/{pedido_id}/concluir/` baixa o Inventário e inclui os produtos produzidos em uma única transação.
- Pedido cancelado: `POST /api/pedido/{pedido_id}/cancelar/` pode registrar o descarte ou criar produto e lote reaproveitado.
- Produto pronto consumido: `POST /api/pedido/{pedido_id}/consumir-estoque/` dá baixa nos lotes por ordem de validade e marca o pedido como concluído.

As movimentações usam as tabelas ativas do MVP, criadas e controladas pelas migrations Django (11 tabelas no total). O Compose não executa `database/create_schema.sql`. Este último é apenas uma referência legada e não deve ser executado no banco da aplicação. Não remova o volume PostgreSQL para atualizar o backend.
