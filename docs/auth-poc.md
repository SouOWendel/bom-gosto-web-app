# POC de Autenticação (Back-end)

## Escopo

POC de autenticação com Django e Django REST Framework, conectada ao PostgreSQL e usando diretamente a tabela `usuario`. Não há integração com API externa.

## Regras de negócio atendidas
- Login com usuário e senha.
- Identificação de primeiro acesso.
- Troca obrigatória de senha no primeiro acesso.
- Logout seguro.
- Sessão persistente no navegador até logout manual ou expiração configurada.

## Pré-requisitos

O banco `db_confeitaria` e a tabela `usuario` devem ser criados pelos scripts em `database/`. No arquivo `apps/backend/.env`, informe os dados da conexão:

```env
POSTGRES_DB=db_confeitaria
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua_senha
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Depois, execute:

```powershell
cd apps/backend
python manage.py migrate
python manage.py runserver
```

O arquivo `.env` contém credenciais e não deve ser enviado ao Git.

## Endpoints

Base local: `http://127.0.0.1:8000/api`

### POST /auth/cadastro-teste/

Cria um usuário temporário para testes locais. Funciona apenas com `DEBUG=True`, recebe somente o login e gera uma senha temporária de seis dígitos.

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

A senha temporária é retornada apenas para o teste e é salva no banco como hash do Django.

### POST /auth/login/

Autentica o usuário e cria uma sessão.

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

Se o usuário já estiver autenticado, a API retorna a mensagem `usuário já está logado.`.

### GET /auth/me/

Retorna os dados do usuário autenticado:

```json
{
  "login": "usuario",
  "primeiro_acesso": true
}
```

### POST /auth/alterar-senha/

Altera a senha do usuário autenticado e define `primeiro_acesso` como `false`.

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

A senha atual deve estar correta, e a nova senha precisa ser diferente e ter pelo menos oito caracteres.

### POST /auth/logout/

Encerra a sessão do usuário autenticado:

```json
{
  "detail": "logout realizado com sucesso."
}
```

## Fluxo completo de teste (PowerShell)

### 1. Criar usuário temporário

```powershell
$body = @{ login = "usuario" } | ConvertTo-Json

$cadastro = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/cadastro-teste/" `
  -ContentType "application/json" `
  -Body $body

$cadastro
```

Guarde o valor retornado em `$cadastro.senha_temporaria`. Para verificar o registro e o valor de `primeiro_acesso`, consulte o banco:

```sql
SELECT id_usuario, login, primeiro_acesso
FROM usuario;
```

### 2. Criar uma sessão e fazer login

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
```

### 3. Consultar o usuário autenticado

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/auth/me/" `
  -WebSession $session
```

O retorno deve mostrar `primeiro_acesso: true` antes da troca de senha.

### 4. Alterar a senha

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

Consulte novamente `/auth/me/`; agora `primeiro_acesso` deve ser `false`.

### 5. Fazer logout

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/logout/" `
  -WebSession $session
```

Depois do logout, uma nova chamada para `/auth/me/` usando `$session` deve retornar `401`.

### 6. Fazer novo login

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