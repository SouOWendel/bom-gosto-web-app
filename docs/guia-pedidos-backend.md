# Guia do back-end de pedidos

## Operacoes disponiveis

| Método  | Rota                | Ação                             |
| ------- | ------------------- | -------------------------------- |
| `POST`  | `/api/pedido/`      | Criar pedido                     |
| `GET`   | `/api/pedido/`      | Listar pedidos                   |
| `GET`   | `/api/pedido/<id>/` | Consultar um pedido              |
| `PATCH` | `/api/pedido/<id>/` | Atualizar parcialmente um pedido |
| `PUT`   | `/api/pedido/<id>/` | Atualizar um pedido              |

A exclusão por `DELETE` não está habilitada: pedidos devem preservar histórico.

## Verificação integrada com Estoque

Ao criar ou consultar um pedido externo de vitrine ou personalizado, cada item da resposta inclui `verificacao_estoque`. Para itens associados a um produto, o campo consulta os lotes válidos do Estoque e retorna o saldo, a disponibilidade e `encaminhar_para_producao` quando a quantidade não for suficiente. O saldo é atual e pode mudar entre consultas. Não é persistido como histórico no pedido.

## 1. Preparar o ambiente

Inicie o Docker Desktop e, no PowerShell, abra a pasta raiz do projeto. Se `docker` não for reconhecido, adicione o executável ao PATH desta janela:

```powershell
$env:Path = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;$env:Path"
```

Suba os três serviços e confira o estado deles:

```powershell
docker compose up --build -d
docker compose ps
```

O backend aplica as migrations antes de iniciar. Se não subir, consulte os logs:

```powershell
docker compose logs --tail 80 backend
```

O frontend fica em `http://localhost:4200` e encaminha `/api` ao backend. O banco usado pelo Compose é `db_confeitaria`.

No terminal do back-end, ative o ambiente virtual e entre na pasta:

```powershell
.\.venv\Scripts\Activate.ps1
Set-Location .\apps\backend
```

Se o PowerShell bloquear a ativação, permita scripts somente nesta janela e tente novamente:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## 2. Carregar os dados de exemplo

Rode o seed depois das migrations:

```powershell
docker compose exec backend python manage.py seed_desenvolvimento
```

O seed carrega clientes, receitas, produtos, pedidos e itens adaptados de `database/insert_data.sql`. Pode ser executado novamente para atualizar esses exemplos.

`database/insert_data.sql` fica como referência histórica. Não execute esse arquivo no banco da aplicação junto com o seed.

O usuário `confeiteira` é criado somente na primeira execução em que ainda não existe. Nessa criação, o terminal exibe uma senha temporária numérica de 6 dígitos. Isso simula a entrega inicial da senha a uma pessoa. O seed não troca nem exibe a senha novamente quando o usuário já existe. Guarde-a quando aparecer.

Se a senha foi perdida ou você quiser testar com outro usuário, crie um login diferente pelo endpoint de desenvolvimento abaixo. Ele também gera uma senha temporária e só fica disponível com `DEBUG` ativo.

## 3. Criar outro usuário de teste

Use outro terminal PowerShell. O comando gera um login único e cria o usuário no backend:

```powershell
$login = "teste_pedidos_$([guid]::NewGuid().ToString('N').Substring(0,8))"
$cadastro = Invoke-RestMethod -Method Post `
   -Uri "http://localhost:4200/api/auth/cadastro-teste/" `
   -ContentType "application/json" `
   -Body (@{ login = $login } | ConvertTo-Json)

$cadastro | Select-Object login, senha_temporaria
```

Anote a senha temporária retornada. Se o login já existir, o endpoint responde `409`; gere outro login.

## 4. Entrar e trocar a senha inicial

Mantenha os próximos comandos no mesmo terminal para preservar a sessão:

```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginBody = @{
   login = $cadastro.login
   senha = $cadastro.senha_temporaria
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
   -Uri "http://localhost:4200/api/auth/login/" `
   -WebSession $session `
   -ContentType "application/json" `
   -Body $loginBody
```

Troque a senha antes de acessar pedidos. A senha nova precisa ter pelo menos 8 caracteres e ser diferente da temporária:

```powershell
$trocaSenha = @{
   senha_atual = $cadastro.senha_temporaria
   nova_senha = "PedidoTeste!2026"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
   -Uri "http://localhost:4200/api/auth/alterar-senha/" `
   -WebSession $session `
   -ContentType "application/json" `
   -Body $trocaSenha
```

O backend responde `403` ao acessar pedidos enquanto `primeiro_acesso` estiver ativo.

## 5. Preparar a sessão para o CRUD

As operações de escrita em pedidos usam autenticação por sessão e token CSRF. Obtenha o token do cookie recebido no login:

```powershell
$csrfCookie = $session.Cookies.GetCookies([uri]"http://localhost:4200") |
   Where-Object Name -eq "csrftoken" |
   Select-Object -First 1
$headers = @{ "X-CSRFToken" = $csrfCookie.Value }
```

Se `$csrfCookie` estiver vazio, faça login novamente com `$session` e repita este passo.

## 6. Criar pedido

O seed cria produtos de exemplo. Para conferir os IDs disponíveis:

```powershell
docker compose exec backend python manage.py shell -c "from pedido.models import Produto; print(list(Produto.objects.values('id_produto', 'nome')))"
```

Crie um pedido interno com o produto de ID `1`, ou substitua pelo ID listado acima:

```powershell
$body = @{
   tipo = "interno"
   valor_total = "10.00"
   valor_sinal = "0.00"
   itens = @(@{
      produto = 1
      quantidade = 1
      preco_unitario = "10.00"
   })
} | ConvertTo-Json -Depth 5

$pedido = Invoke-RestMethod -Method Post `
   -Uri "http://localhost:4200/api/pedido/" `
   -WebSession $session -Headers $headers `
   -ContentType "application/json" -Body $body

$pedido
```

A resposta inclui `id_pedido`, usado nas consultas e atualizações seguintes.

## 7. Consultar pedidos

Liste todos os pedidos:

```powershell
Invoke-RestMethod -Method Get `
   -Uri "http://localhost:4200/api/pedido/" `
   -WebSession $session
```

Consulte o pedido criado:

```powershell
Invoke-RestMethod -Method Get `
   -Uri "http://localhost:4200/api/pedido/$($pedido.id_pedido)/" `
   -WebSession $session
```

## 8. Atualizar pedido

`PATCH` altera somente os campos enviados:

```powershell
$alteracao = @{ forma_pagamento = "pix" } | ConvertTo-Json

Invoke-RestMethod -Method Patch `
   -Uri "http://localhost:4200/api/pedido/$($pedido.id_pedido)/" `
   -WebSession $session -Headers $headers `
   -ContentType "application/json" -Body $alteracao
```

`PUT` também está disponível para enviar a representação completa do pedido. Depois da atualização, consulte-o com `GET` para confirmar a alteração.

## Regras e testes

Cada item deve informar exatamente um produto ou uma receita. Pedidos internos não devem ter subtipo. Pedidos externos exigem cliente e subtipo, e o sinal deve ser zero ou metade do valor total. Valores negativos são rejeitados.

O `DELETE` deve responder `405 Method Not Allowed`; o pedido continua consultável porque a exclusão não faz parte do módulo.

Para rodar os testes automatizados existentes:

```powershell
docker compose exec backend python manage.py test pedido
```
