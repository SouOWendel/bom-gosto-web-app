# POC de Autenticacao

## Escopo

Esta POC implementa autenticacao com Django REST Framework no back-end e Angular no front-end. A autenticacao usa a sessao do Django, armazenada em cookie, e nao JWT.

O SQLite local fica em `apps/backend/db.sqlite3`. Os usuarios de login sao registros do modelo padrao `django.contrib.auth.models.User`; o status de primeiro acesso fica em `usuario_perfilusuario`.

## Regras de negocio

- Login com usuario e senha.
- Identificacao de primeiro acesso.
- Alteracao da senha atual.
- Definicao de `primeiro_acesso = false` apos a troca de senha.
- Logout no back-end, invalidando a sessao.
- Persistencia da sessao ate o logout manual ou a expiracao configurada.

## Preparar o ambiente

Execute os comandos a partir das pastas indicadas.

### Banco e usuario

```powershell
cd apps/backend
python manage.py migrate
python manage.py createsuperuser
```

O comando `createsuperuser` solicita o login, e-mail e senha. A senha deve ser criada pelo Django; nao insira senha diretamente com SQL.

Para criar um usuario comum sem interacao:

```powershell
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_user(username='usuario', email='usuario@example.com', password='SenhaSegura123')"
```

### Iniciar os servidores

Terminal do back-end:

```powershell
cd apps/backend
python manage.py runserver
```

Terminal do front-end:

```powershell
cd apps/frontend
npm start
```

O Angular fica em `http://localhost:4200` e o Django em `http://127.0.0.1:8000`. Durante o desenvolvimento, [proxy.conf.json](../apps/frontend/proxy.conf.json) encaminha `/api` do Angular para o Django.

## Login pelo front-end

1. Abra `http://localhost:4200/auth/login`.
2. Informe o usuario criado no Django.
3. Informe a senha.
4. O front-end envia `POST /api/auth/login/` com `{ "login": "...", "senha": "..." }`.
5. Em caso de sucesso, a sessao Django e mantida pelo navegador e o usuario e direcionado para `/dashboard`.

Se `primeiro_acesso` for `true`, a senha deve ser alterada usando o endpoint de troca de senha antes de considerar o primeiro acesso concluido.

## Endpoints

Base direta do back-end: `http://127.0.0.1:8000/api`

Ao usar o front-end, utilize o prefixo `/api` com o proxy, por exemplo: `http://localhost:4200/api/auth/login/`.

### POST /auth/login/

Autentica o usuario e cria a sessao Django.

Body:

```json
{
  "login": "admin",
  "senha": "bomgosto123"
}
```

Resposta:

```json
{
  "autenticado": true,
  "login": "admin",
  "primeiro_acesso": true
}
```

### GET /auth/me/

Retorna o usuario autenticado. A requisicao precisa manter o cookie de sessao.

Resposta:

```json
{
  "login": "admin",
  "primeiro_acesso": false
}
```

### POST /auth/alterar-senha/

Altera a senha do usuario autenticado e define `primeiro_acesso = false`.

Body:

```json
{
  "senha_atual": "bomgosto123",
  "nova_senha": "BomGosto@2026"
}
```

Resposta:

```json
{
  "detail": "senha alterada com sucesso.",
  "primeiro_acesso": false
}
```

### POST /auth/logout/

Encerra a sessao do usuario autenticado.

Resposta:

```json
{
  "detail": "logout realizado com sucesso."
}
```

## Validar a API pelo PowerShell

O `WebRequestSession` preserva o cookie de sessao entre as requisicoes:

```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/auth/login/" -WebSession $session -ContentType "application/json" -Body '{"login":"admin","senha":"bomgosto123"}'

Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/auth/me/" -WebSession $session

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/auth/alterar-senha/" -WebSession $session -ContentType "application/json" -Body '{"senha_atual":"bomgosto123","nova_senha":"BomGosto@2026"}'

Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/auth/me/" -WebSession $session

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/auth/logout/" -WebSession $session
```

## Respostas de erro comuns

- `400`: campos obrigatorios ausentes.
- `401`: credenciais invalidas ou sessao inexistente.
- `404` em `http://localhost:4200/api/...`: reinicie o Angular para carregar o proxy e confirme que o Django esta rodando na porta 8000.
- `404` em `http://127.0.0.1:8000/api/...`: confirme a URL, incluindo a barra final, e verifique se o back-end esta em execucao.
