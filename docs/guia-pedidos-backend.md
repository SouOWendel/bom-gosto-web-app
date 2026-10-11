# Guia do back-end de pedidos

## Operações disponíveis

| Método | Rota | Ação |
|---|---|---|
| `POST` | `/api/pedido/` | Criar pedido |
| `GET` | `/api/pedido/` | Listar pedidos |
| `GET` | `/api/pedido/<id>/` | Consultar um pedido |
| `PATCH` | `/api/pedido/<id>/` | Atualizar parcialmente um pedido |
| `PUT` | `/api/pedido/<id>/` | Atualizar um pedido |

A exclusão por `DELETE` não está habilitada: pedidos devem preservar histórico.

## Preparar o ambiente

1. Inicie o Docker Desktop e abra o terminal do VS Code na raiz do repositório.
2. Se o comando `docker` não for reconhecido no PowerShell, adicione o diretório do Docker ao PATH da janela atual:

   ```powershell
   env:Path+=";env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin"
   ```

3. Inicie o serviço PostgreSQL:

   ```powershell
   docker compose up -d postgres
   docker ps
   ```

   Confirme que o contêiner do banco está em execução e saudável.

4. No terminal do back-end, ative o ambiente virtual e entre na pasta:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   Set-Location .\apps\backend
   ```

   Se o PowerShell bloquear a ativação, permita scripts somente nesta janela e tente novamente:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
   .\.venv\Scripts\Activate.ps1
   ```

5. Configure as variáveis do PostgreSQL nesse mesmo terminal, usando os valores locais configurados no projeto:

   ```powershell
   $env:POSTGRES_DB = "bom_gosto_db"
   $env:POSTGRES_USER = "postgres"
   $env:POSTGRES_PASSWORD = "SENHA_LOCAL_DO_POSTGRES"
   $env:POSTGRES_HOST = "127.0.0.1"
   $env:POSTGRES_PORT = "5432"
   ```

   Não publique senhas reais no README, neste guia ou no Git.

6. Inicie o servidor Django:

   ```powershell
   python manage.py runserver
   ```

   Deixe esse terminal aberto. A API local ficará disponível em `http://127.0.0.1:8000`.

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



