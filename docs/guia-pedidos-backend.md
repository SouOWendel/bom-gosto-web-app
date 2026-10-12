# Guia do back-end de pedidos

## Operações disponíveis

| Método  | Rota                | Ação                             |
| ------- | ------------------- | -------------------------------- |
| `POST`  | `/api/pedido/`      | Criar pedido                     |
| `GET`   | `/api/pedido/`      | Listar pedidos                   |
| `GET`   | `/api/pedido/<id>/` | Consultar um pedido              |
| `PATCH` | `/api/pedido/<id>/` | Atualizar parcialmente um pedido |
| `PUT`   | `/api/pedido/<id>/` | Atualizar um pedido              |

A exclusão por `DELETE` não está habilitada: pedidos devem preservar histórico.

## Preparar o ambiente

1. Inicie o Docker Desktop e abra o terminal do VS Code na raiz do repositorio.
2. Inicie o ambiente completo:

   ```powershell
   docker compose up -d --build
   docker compose ps
   ```

   O PostgreSQL precisa aparecer como `healthy`. O backend aplica as migrations automaticamente e fica disponível em `http://127.0.0.1:8000`.

3. Se precisar verificar o banco:

   ```powershell
   docker compose exec -T postgres psql -U postgres -d bom_gosto_db -c "SELECT current_database(), current_user;"
   ```

   O frontend fica disponível em `http://localhost:4200`. Para parar o ambiente sem apagar dados, use `docker compose down`.

O fluxo local sem Docker continua possível, mas exige PostgreSQL instalado no host, um ambiente virtual Python, as variáveis `POSTGRES_*` apontando para `127.0.0.1` e a execução manual de `migrate` e `runserver`. Consulte [config-postgresql.md](config-postgresql.md) se precisar desse cenário.

## Autenticar para testar

Em outro terminal PowerShell, faça login com uma conta válida, cuja senha inicial já tenha sido alterada:

```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginBody = '{"login":"SEU_LOGIN","senha":"SUA_SENHA"}'

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/auth/login/" -WebSession $session -ContentType "application/json" -Body $loginBody
```

Os `POST` e `PATCH` também precisam do token CSRF. Obtenha-o do cookie recebido durante o login:

```powershell
$csrfCookie = $session.Cookies.GetCookies([uri]"http://127.0.0.1:8000") | Where-Object Name -eq "csrftoken" | Select-Object -First 1
$headers = @{ "X-CSRFToken" = $csrfCookie.Value }
```

Mantenha o mesmo terminal para preservar `session`,`csrfCookie` e `$headers`.

## Criar um pedido de teste

O exemplo cria um pedido interno com o produto de ID `1`. Use o ID de um produto existente no banco:

```powershell
$pedidoBody = '{"tipo":"interno","valor_total":"10.00","valor_sinal":"0.00","itens":[{"produto":1,"quantidade":1,"preco_unitario":"10.00"}]}'

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/pedido/" -WebSession $session -Headers $headers -ContentType "application/json" -Body $pedidoBody
```

A resposta deve incluir o ID do pedido criado, seu status e os itens associados.

## Consultar pedidos

Listar:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/pedido/" -WebSession $session
```

Consultar um pedido específico, substituindo `1` pelo ID retornado na criação:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/pedido/1/" -WebSession $session
```

## Atualizar um pedido

O exemplo atualiza a forma de pagamento do pedido de teste:

```powershell
$atualizacao = '{"forma_pagamento":"pix"}'

Invoke-RestMethod -Method Patch -Uri "http://127.0.0.1:8000/api/pedido/1/" -WebSession $session -Headers $headers -ContentType "application/json" -Body $atualizacao
```

Faça um `GET` do pedido para confirmar a alteração.
