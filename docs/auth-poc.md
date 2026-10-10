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

## Preparar o ambiente

O banco `db_confeitaria` e a tabela `usuario` devem ser criados pelos scripts em `database/`. O Django usa a tabela `usuario` existente e nao a recria.

Crie `apps/backend/.env` com os dados da conexao:

```env
POSTGRES_DB=db_confeitaria
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua_senha
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

O arquivo `.env` contem credenciais e nao deve ser enviado ao Git.

Execute os comandos em terminais separados:

```powershell
cd apps/backend
python manage.py migrate
python manage.py runserver
```

```powershell
cd apps/frontend
npm install
npm start
```

O Angular fica em `http://localhost:4200` e o Django em `http://127.0.0.1:8000`. O [proxy do Angular](../apps/frontend/proxy.conf.json) encaminha `/api` para o Django.

## Integracao com o front-end

Abra `http://localhost:4200/auth/login`. O Angular envia as requisicoes para `/api`, preserva o cookie da sessao com `withCredentials` e usa `primeiro_acesso` para decidir entre a tela de troca de senha e o dashboard.

O front-end nao acessa o PostgreSQL diretamente.

## Endpoints

Base direta do back-end: `http://127.0.0.1:8000/api`

Ao usar o front-end, o proxy utiliza o mesmo caminho com `http://localhost:4200/api`.

### POST /auth/cadastro-teste/

Cria um usuario temporario para testes locais. Funciona somente com `DEBUG=True`, recebe apenas o login e gera uma senha temporaria de seis digitos.

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

### POST /auth/login/

Autentica o usuario e cria uma sessao Django.

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

Se o usuario ja estiver autenticado, retorna `409`. Login ou senha ausentes retornam `400`; credenciais invalidas retornam `401`.

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

Altera a senha do usuario autenticado e define `primeiro_acesso` como `false`.

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

Encerra a sessao do usuario autenticado:

```json
{
  "detail": "logout realizado com sucesso."
}
```

## Fluxo completo de teste no PowerShell

### 1. Criar usuario temporario

```powershell
$body = @{ login = "usuario" } | ConvertTo-Json

$cadastro = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/cadastro-teste/" `
  -ContentType "application/json" `
  -Body $body

$cadastro
```

Guarde `$cadastro.senha_temporaria`. Para consultar o usuario sem expor o hash da senha:

```sql
SELECT id_usuario, login, primeiro_acesso
FROM usuario;
```

### 2. Fazer login e consultar a sessao

```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

$body = @{
  login = "usuario"
  senha = $cadastro.senha_temporaria
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/login/" `
  -WebSession $session `
  -ContentType "application/json" `
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
  -Body $body
```

Consulte `/auth/me/` novamente. Agora `primeiro_acesso` deve ser `false`.

### 4. Fazer logout

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/logout/" `
  -WebSession $session
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
  -Body $body
```

O retorno deve indicar `primeiro_acesso: false`.

## Respostas de erro comuns

- `400`: campos obrigatorios ausentes ou nova senha invalida.
- `401`: credenciais invalidas ou sessao inexistente.
- `404`: rota incorreta, barra final ausente ou endpoint de cadastro acessado com `DEBUG=False`.
- `409`: usuario ja esta logado ou login ja cadastrado.

Se o Angular retornar `404` em `/api/...`, reinicie o servidor Angular para carregar o proxy e confirme que o Django esta rodando na porta `8000`.