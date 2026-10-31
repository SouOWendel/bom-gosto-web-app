<<<<<<< HEAD
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

As movimentações usam os registros atuais do schema. Não execute o script de criação do schema contra um banco existente e não remova o volume PostgreSQL para atualizar o backend.
=======
# Guia do back-end de estoque

Este guia descreve como iniciar o projeto com Docker e testar manualmente a API de Estoque usando PowerShell.

## Escopo e persistência

O módulo permite cadastrar, consultar e atualizar lotes de produtos finais prontos para entrega imediata. A exclusão não está disponível. Também disponibiliza uma consulta de saldo para que Pedidos possa verificar quantidade e encaminhar à Produção os itens sem saldo suficiente.

O model Django mapeia a tabela `estoque` definida em `database/create_schema.sql`. A API usa a relação já existente com `produto`.

Cada linha representa um lote de um produto. A consulta de disponibilidade soma os lotes com validade nula ou igual/posterior à data atual. Lotes vencidos continuam consultáveis, mas não contam como disponíveis. A mesma lógica é chamada pelo módulo Pedidos para verificar os itens de pedidos externos de vitrine ou personalizados. A resposta indica o encaminhamento para Produção, sem criar automaticamente uma solicitação nesse módulo.

## Pré-requisitos

- Docker Desktop em execução.
- PowerShell aberto na raiz do repositório.
- Tabelas `estoque` e `produto` presentes no banco `db_confeitaria`.
- Usuário autenticado com a senha inicial já alterada.

## 1. Iniciar o ambiente e conferir o schema

```powershell
docker compose up --build -d
docker compose ps
```

Confirme que as colunas do estoque existem:

```powershell
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'estoque'"
```

O resultado deve conter `id_estoque`, `id_produto`, `quantidade_disponivel`, `data_validade` e `custo`. Se o resultado estiver vazio, o volume atual não recebeu o schema inicial. Preserve os dados: não use `docker compose down -v`.

## 2. Autenticar

Siga as etapas 3 e 4 do [guia de Inventário](guia-inventario-backend.md) para criar uma conta temporária, autenticar e trocar a senha inicial. Execute os comandos na mesma janela PowerShell para preservar os cookies.

## 3. Consultar produtos para teste

Escolha um `id_produto` existente:

```powershell
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT id_produto, nome FROM produto ORDER BY id_produto"
```

## 4. Criar um lote

Defina o ID de um produto existente e envie os dados do lote.

```powershell
$produtoId = 1
$estoqueBody = @{
  id_produto = $produtoId
  quantidade_disponivel = "4.00"
  data_validade = "2027-01-31"
  custo = "12.50"
} | ConvertTo-Json

$lote = Invoke-RestMethod -Method Post `
  -Uri "$base/api/estoque/" `
  -WebSession $session -Headers $headers `
  -ContentType "application/json" -Body $estoqueBody

$lote
$idEstoque = $lote.id_estoque
```

## 5. Consultar e listar lotes

```powershell
Invoke-RestMethod -Method Get `
  -Uri "$base/api/estoque/$idEstoque/" `
  -WebSession $session

Invoke-RestMethod -Method Get `
  -Uri "$base/api/estoque/" `
  -WebSession $session
```

O campo `vencido` é calculado a partir da validade do lote e da data atual.

## 6. Consultar disponibilidade para um pedido

Informe o produto e a quantidade necessária. A API soma somente os lotes ainda válidos.

```powershell
Invoke-RestMethod -Method Get `
  -Uri "$base/api/estoque/disponibilidade/?id_produto=$produtoId&quantidade=3.00" `
  -WebSession $session
```

Se o saldo válido for insuficiente, a resposta terá `disponivel = false` e `encaminhar_para_producao = true`, conforme o fluxo de verificação descrito no requisito RN02.

## 7. Atualizar o lote

```powershell
$patchBody = @{ quantidade_disponivel = "6.00" } | ConvertTo-Json

Invoke-RestMethod -Method Patch `
  -Uri "$base/api/estoque/$idEstoque/" `
  -WebSession $session -Headers $headers `
  -ContentType "application/json" -Body $patchBody
```

`PUT` também pode ser usado para atualização completa; `PATCH` altera apenas os campos enviados.

## 8. Conferir validação e ausência de exclusão

Quantidade negativa deve retornar `400 Bad Request`; `DELETE` deve retornar `405 Method Not Allowed`.

```powershell
$bodyInvalido = @{
  id_produto = $produtoId
  quantidade_disponivel = "-1.00"
} | ConvertTo-Json

try {
  Invoke-RestMethod -Method Post `
    -Uri "$base/api/estoque/" `
    -WebSession $session -Headers $headers `
    -ContentType "application/json" -Body $bodyInvalido
} catch {
  [int]$_.Exception.Response.StatusCode
}

try {
  Invoke-RestMethod -Method Delete `
    -Uri "$base/api/estoque/$idEstoque/" `
    -WebSession $session -Headers $headers
} catch {
  [int]$_.Exception.Response.StatusCode
}
```

## 9. Executar os testes automatizados

```powershell
docker compose exec backend python manage.py test estoque
```
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
