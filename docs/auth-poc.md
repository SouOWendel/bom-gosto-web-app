# POC de Autenticacao

## Escopo

POC de autenticacao com Django REST Framework no back-end e Angular no front-end. O back-end usa PostgreSQL, a tabela `usuario` existente e sessoes Django armazenadas em cookie. Nao ha JWT nem integracao com API externa.

## Regras de negocio

- Login com usuario e senha.
- Identificacao de primeiro acesso.
- Cadastro de usuario temporario para testes locais.
- Alteracao da senha atual.
- Definicao de `primeiro_acesso = false` apos a troca de senha.
- Logout no back-end, invalidando a sessao.
- Persistencia da sessao ate o logout manual ou a expiracao configurada.

## Preparar o ambiente com Docker

Na raiz do repositorio, inicie o ambiente:

```powershell
docker compose up -d --build
docker compose ps
```

O Compose usa o banco `db_confeitaria` e inicia o backend com `python manage.py migrate --noinput`. As migrations Django criam e controlam as 11 tabelas ativas de aplicação, incluindo `usuario`. O Compose não executa `database/create_schema.sql`. Este último é apenas uma referência legada.

O cadastro temporario fica desabilitado por padrao, mesmo em Docker. Para habilita-lo somente no ambiente local, defina `ENABLE_TEST_USER_REGISTRATION=1` antes de iniciar/recriar o servico `backend`. O endpoint tambem exige `DEBUG=True` e CSRF. Em ambientes fora de desenvolvimento, defina `DJANGO_SECRET_KEY` e mantenha `DEBUG=False`.

O Angular fica em `http://localhost:4200` e o Django em `http://127.0.0.1:8000`. O [proxy do Angular](../apps/frontend/proxy.conf.json) encaminha `/api` para `http://backend:8000` dentro da rede Docker.

Para conferir a conexao e os usuarios:

```powershell
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT current_database(), current_user"
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT id_usuario, login, primeiro_acesso FROM usuario"
```

A alternativa de executar Django e Angular diretamente no host exige um PostgreSQL local e variaveis `POSTGRES_*` apontando para `localhost`. Para o fluxo oficial, use o Docker Compose.

## Integracao com o front-end

Abra `http://localhost:4200/auth/login`. O Angular envia as requisicoes para `/api`, preserva o cookie da sessao com `withCredentials` e usa `primeiro_acesso` para decidir entre a tela de troca de senha e o dashboard.

O front-end nao acessa o PostgreSQL diretamente.

Antes do login ou de qualquer requisição que altere dados, consulte `GET /auth/csrf/` e envie o cookie `csrftoken` tambem no cabecalho `X-CSRFToken`. O login rotaciona o token CSRF. Por isso, o front-end deve ler o cookie atualizado em cada requisicao, em vez de reutilizar o token anterior ao login. Requisicoes `GET` nao precisam do cabecalho.

## Endpoints

Base direta do back-end: `http://127.0.0.1:8000/api`

Ao usar o front-end, o proxy utiliza o mesmo caminho com `http://localhost:4200/api`.

### POST /auth/cadastro-teste/

Cria um usuario temporario para testes locais. Exige `DEBUG=True` e `ENABLE_TEST_USER_REGISTRATION=1`, recebe apenas o login e gera uma senha temporaria de seis digitos. A opcao fica desabilitada por padrao.

Body:

```json
{
  "login": "usuario"
}
```

Resposta:

```json
{
  "login": "usuario",
  "senha_temporaria": "123456",
  "primeiro_acesso": true
}
```

A senha temporaria e retornada para o teste e salva no banco como hash compativel com o Django. Em producao, esse endpoint deve permanecer desabilitado.
Como toda operacao `POST`, exige o token CSRF obtido por `GET /auth/csrf/`.

### GET /auth/csrf/

Garante o cookie `csrftoken` e retorna um token que pode ser enviado no cabecalho `X-CSRFToken`:

```json
{
  "csrf_token": "token-csrf"
}
```

### POST /auth/login/

Autentica o usuario e cria uma sessao Django. Exige o token CSRF obtido por `GET /auth/csrf/`. O login rotaciona o token, entao obtenha o valor atualizado do cookie `csrftoken` antes da proxima requisicao mutavel.

Body:

```json
{
  "login": "usuario",
  "senha": "senha_temporaria"
}
```

Resposta:

```json
{
  "autenticado": true,
  "login": "usuario",
  "primeiro_acesso": true
}
```

Se o usuario ja estiver autenticado, retorna `409`. Login ou senha ausentes retornam `400`. Credenciais invalidas retornam `401`.

### GET /auth/me/

Retorna os dados do usuario autenticado. A requisicao precisa manter o cookie da sessao.

Resposta:

```json
{
  "login": "usuario",
  "primeiro_acesso": true
}
```

Sem uma sessao valida, retorna `401`.

### POST /auth/alterar-senha/

Altera a senha do usuario autenticado e define `primeiro_acesso` como `false`. Exige sessao autenticada e token CSRF.

Body:

```json
{
  "senha_atual": "senha_temporaria",
  "nova_senha": "nova_senha"
}
```

Resposta:

```json
{
  "detail": "senha alterada com sucesso.",
  "primeiro_acesso": false
}
```

A senha atual deve estar correta. A nova senha deve ser diferente e ter pelo menos oito caracteres.

### POST /auth/logout/

Encerra a sessao do usuario autenticado. Exige sessao autenticada e token CSRF:

```json
{
  "detail": "logout realizado com sucesso."
}
```

## Fluxo completo de teste no PowerShell

### 1. Criar usuario temporario

O endpoint abaixo fica desabilitado por padrao. Para habilitar no Docker local, defina a variavel `ENABLE_TEST_USER_REGISTRATION=1` e recrie somente o servico backend. Não remova o volume do banco. Antes de chamar o endpoint, obtenha o token CSRF como mostrado abaixo.

**cURL (Linux / macOS / Git Bash):**

```bash
csrf=$(curl -s -c cookies.txt http://127.0.0.1:8000/api/auth/csrf/ | jq -r .csrf_token)
curl -X POST http://127.0.0.1:8000/api/auth/cadastro-teste/ \
  -b cookies.txt -c cookies.txt \
  -H "X-CSRFToken: $csrf" \
  -H "Content-Type: application/json" \
  -d '{"login": "usuario"}'
```

**PowerShell (Windows):**

```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/auth/csrf/" `
  -WebSession $session

function Get-CsrfHeaders {
  $cookie = $session.Cookies.GetCookies([uri]"http://127.0.0.1:8000")["csrftoken"]
  return @{ "X-CSRFToken" = $cookie.Value }
}

$body = @{ login = "usuario" } | ConvertTo-Json

$cadastro = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/cadastro-teste/" `
  -ContentType "application/json" `
  -Headers (Get-CsrfHeaders) `
  -WebSession $session `
  -Body $body

$cadastro
```

Guarde a senha temporaria retornada. Para consultar o usuario sem expor o hash da senha:

```sql
SELECT id_usuario, login, primeiro_acesso
FROM usuario;
```

### 2. Fazer login e consultar a sessao

```powershell
$body = @{
  login = "usuario"
  senha = $cadastro.senha_temporaria
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/login/" `
  -WebSession $session `
  -ContentType "application/json" `
  -Headers (Get-CsrfHeaders) `
  -Body $body

Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/auth/me/" `
  -WebSession $session
```

O retorno de `/auth/me/` deve mostrar `primeiro_acesso: true` antes da troca de senha.

### 3. Alterar a senha

```powershell
$body = @{
  senha_atual = $cadastro.senha_temporaria
  nova_senha = "nova_senha"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/alterar-senha/" `
  -WebSession $session `
  -ContentType "application/json" `
  -Headers (Get-CsrfHeaders) `
  -Body $body
```

Consulte `/auth/me/` novamente. Agora `primeiro_acesso` deve ser `false`.

### 4. Fazer logout

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/logout/" `
  -WebSession $session `
  -Headers (Get-CsrfHeaders)
```

Depois do logout, uma chamada para `/auth/me/` usando a mesma sessao deve retornar `401`.

### 5. Fazer novo login

```powershell
$body = @{ login = "usuario"; senha = "nova_senha" } | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/login/" `
  -WebSession $session `
  -ContentType "application/json" `
  -Headers (Get-CsrfHeaders) `
  -Body $body
```

O retorno deve indicar `primeiro_acesso: false`.

## Respostas de erro comuns

- `400`: campos obrigatorios ausentes ou nova senha invalida.
- `401`: credenciais invalidas ou sessao inexistente.
- `404`: rota incorreta, barra final ausente ou endpoint de cadastro acessado com `DEBUG=False`.
- `409`: usuario ja esta logado ou login ja cadastrado.

Se o Angular retornar `404` em `/api/...`, reinicie o servidor Angular para carregar o proxy e confirme que o Django esta rodando na porta `8000`.
