# Guia do back-end de inventário

<<<<<<< HEAD
As respostas incluem `data_validade`, `abaixo_do_minimo` e `alerta_validade`. O alerta usa `critico` (vencido ou vence hoje), `atencao` (até sete dias) e `preventivo` (até quinze dias). `unidade_medida` não existe na tabela atual e não é exposta pela API. Para produção e baixa de ingredientes, consulte [Contratos da API operacional](api-fluxos-operacionais.md).

=======
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
Este guia descreve como iniciar o projeto com Docker e testar manualmente a API de Inventário usando PowerShell.

## Escopo e persistência

O módulo expõe operações de criação, consulta e atualização de ingredientes. A exclusão não está disponível.

O model Django mapeia a tabela `ingrediente`, definida em `database/create_schema.sql`, com `managed = False`. A API usa o PostgreSQL configurado no Docker Compose para ler e gravar ingredientes, mas o Django não cria nem altera essa tabela por migrations. A tabela deve existir no banco antes de usar os endpoints.

Em uma instalação nova, o Compose executa `database/create_schema.sql` quando cria o volume PostgreSQL. Os scripts de inicialização não são executados novamente em um volume já existente. Não execute `makemigrations` para o app `inventario` nem `database/create_schema.sql` completo contra um banco existente.

## Pré-requisitos

- Docker Desktop em execução.
- PowerShell aberto na raiz do repositório.
- Tabela `ingrediente` presente no banco `db_confeitaria`.

## 1. Iniciar o ambiente

```powershell
docker compose up --build -d
docker compose ps
```

O backend executa as migrations dos outros apps já configurados e inicia o servidor. Até o momento, o app `inventario` não tem migration própria.

Se algum serviço não iniciar, consulte os logs:

```powershell
docker compose logs --tail 80 backend
docker compose logs --tail 80 postgres
```

A API fica disponível em `http://127.0.0.1:8000/api`.

## 2. Confirmar que a tabela existe

O model é `managed = False`, portanto não cria a tabela. Confirme que o schema inicial criou `ingrediente`:

```powershell
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'ingrediente'"
```

O resultado deve conter `id_ingrediente`, `nome`, `quantidade_disponivel`, `custo_unitario`, `data_validade` e `quantidade_minima`. Se não houver linhas, pare aqui: o banco existente não recebeu o schema inicial. Não recrie o volume com `docker compose down -v` se precisar preservar os dados.

## 3. Criar um usuário temporário de teste

O endpoint de cadastro de teste está disponível somente com `DEBUG` ativo. Gere um login único:

```powershell
$base = "http://127.0.0.1:8000"
$login = "teste_inventario_$([guid]::NewGuid().ToString('N').Substring(0,8))"
$cadastro = Invoke-RestMethod -Method Post `
  -Uri "$base/api/auth/cadastro-teste/" `
  -ContentType "application/json" `
  -Body (@{ login = $login } | ConvertTo-Json)

$cadastro | Select-Object login, senha_temporaria
```

Guarde a senha temporária exibida para fazer login e trocá-la. O endpoint cria o usuário no banco. Os comandos seguintes usam `$cadastro.login` e `$cadastro.senha_temporaria`, portanto mantenha essa variável nesta janela do PowerShell.

## 4. Obter o token CSRF, entrar e trocar a senha inicial

Faça os próximos comandos na mesma janela para manter os cookies de sessão:

```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

# Obtém o cookie CSRF do mesmo host usado nas chamadas da API.
Invoke-WebRequest -Uri "$base/admin/login/" `
  -Method Get -WebSession $session -UseBasicParsing | Out-Null

$loginBody = @{
  login = $cadastro.login
  senha = $cadastro.senha_temporaria
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri "$base/api/auth/login/" `
  -WebSession $session `
  -ContentType "application/json" -Body $loginBody

# O login pode rotacionar o token CSRF. Leia o cookie atualizado da sessão
$csrfCookie = $session.Cookies.GetCookies([uri]$base) |
  Where-Object Name -eq "csrftoken" |
  Select-Object -First 1
if (-not $csrfCookie) {
  throw "Cookie CSRF não encontrado. Confira o login e repita esta etapa."
}
$headers = @{ "X-CSRFToken" = $csrfCookie.Value }
```

Troque a senha inicial antes de acessar o Inventário:

```powershell
$novaSenha = "InventarioTeste!2026"
$alteracaoSenha = @{
  senha_atual = $cadastro.senha_temporaria
  nova_senha = $novaSenha
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri "$base/api/auth/alterar-senha/" `
  -WebSession $session -Headers $headers `
  -ContentType "application/json" -Body $alteracaoSenha
```

As operações de escrita do CRUD também enviam o cabeçalho `X-CSRFToken`, necessário para autenticação por sessão.

## 5. Criar um ingrediente

Use um nome identificável para facilitar a conferência e a limpeza manual posterior:

```powershell
$ingredienteBody = @{
  nome = "TESTE INVENTARIO - Farinha"
  quantidade_disponivel = "4.50"
  custo_unitario = "3.25"
  data_validade = "2027-01-31"
  quantidade_minima = "5.00"
} | ConvertTo-Json

$ingrediente = Invoke-RestMethod -Method Post `
  -Uri "$base/api/inventario/ingrediente/" `
  -WebSession $session -Headers $headers `
  -ContentType "application/json" -Body $ingredienteBody

$ingrediente
$idIngrediente = $ingrediente.id_ingrediente
```

A resposta deve incluir `id_ingrediente` e `abaixo_do_minimo = true`, pois `4.50` é menor que `5.00`.

## 6. Consultar o ingrediente

Consulte o registro individual:

```powershell
Invoke-RestMethod -Method Get `
  -Uri "$base/api/inventario/ingrediente/$idIngrediente/" `
  -WebSession $session
```

Liste os ingredientes:

```powershell
Invoke-RestMethod -Method Get `
  -Uri "$base/api/inventario/ingrediente/" `
  -WebSession $session
```

## 7. Atualizar parcialmente com `PATCH`

Altere apenas a quantidade disponível:

```powershell
$patchBody = @{ quantidade_disponivel = "6.00" } | ConvertTo-Json

Invoke-RestMethod -Method Patch `
  -Uri "$base/api/inventario/ingrediente/$idIngrediente/" `
  -WebSession $session -Headers $headers `
  -ContentType "application/json" -Body $patchBody
```

A resposta deve mostrar `abaixo_do_minimo = false`, pois `6.00` é maior que o mínimo de `5.00`.

## 8. Atualizar o ingrediente com `PUT`

Envie a representação do ingrediente. Como `PUT` atualiza todos os campos enviados, inclua os campos opcionais que deseja substituir. Os opcionais omitidos permanecem com os valores atuais:

```powershell
$putBody = @{
  nome = "TESTE INVENTARIO - Farinha"
  quantidade_disponivel = "3.00"
  custo_unitario = "3.50"
  data_validade = "2027-02-28"
  quantidade_minima = "5.00"
} | ConvertTo-Json

Invoke-RestMethod -Method Put `
  -Uri "$base/api/inventario/ingrediente/$idIngrediente/" `
  -WebSession $session -Headers $headers `
  -ContentType "application/json" -Body $putBody
```

Como a quantidade voltou a ficar abaixo de `5.00`, a resposta deve mostrar `abaixo_do_minimo = true`.

## 9. Conferir validação e ausência de exclusão

Uma quantidade negativa deve retornar `400 Bad Request`:

```powershell
$bodyInvalido = @{
  nome = "TESTE INVENTARIO - Invalido"
  quantidade_disponivel = "-1.00"
} | ConvertTo-Json

try {
  Invoke-RestMethod -Method Post `
    -Uri "$base/api/inventario/ingrediente/" `
    -WebSession $session -Headers $headers `
    -ContentType "application/json" -Body $bodyInvalido
} catch {
  [int]$_.Exception.Response.StatusCode
}
```

O método `DELETE` não faz parte do CRUD e deve retornar `405 Method Not Allowed`:

```powershell
try {
  Invoke-RestMethod -Method Delete `
    -Uri "$base/api/inventario/ingrediente/$idIngrediente/" `
    -WebSession $session -Headers $headers
} catch {
  [int]$_.Exception.Response.StatusCode
}
```

<<<<<<< HEAD
O registro não é removido pelo teste. Confirme o estado final com `GET` ou com a consulta SQL da etapa 2. A limpeza de registros de teste deve ser feita de acordo com o procedimento de manutenção do banco do projeto.
=======
O registro não é removido pelo teste. Confirme o estado final com `GET` ou com a consulta SQL da etapa 2. A limpeza de registros de teste deve ser feita de acordo com o procedimento de manutenção do banco do projeto.
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
