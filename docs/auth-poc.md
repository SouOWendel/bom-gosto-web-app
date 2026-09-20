# POC de Autenticação (Back-end)

## Escopo desta entrega
Implementação da prova de conceito de autenticação no back-end com Django/DRF, sem integração com API externa e sem alterações no front-end.

## Regras de negócio atendidas
- Login com usuário e senha.
- Identificação de primeiro acesso.
- Troca obrigatória de senha no primeiro acesso.
- Logout seguro.
- Sessão persistente no navegador até logout manual ou expiração configurada.

## Endpoints
Base local: `http://127.0.0.1:8000/api`

### POST /auth/login/
Autentica usuário e retorna status de primeiro acesso.

Exemplo de body:
```json
{
  "login": "admin",
  "senha": "bomgosto123"
}
```

Exemplo de resposta:
```json
{
  "autenticado": true,
  "login": "admin",
  "primeiro_acesso": true
}
```

### POST /auth/alterar-senha/
Altera a senha do usuário autenticado e define primeiro_acesso = false.

Exemplo de body:
```json
{
  "senha_atual": "bomgosto123",
  "nova_senha": "BomGosto@2026"
}
```

Exemplo de resposta:
```json
{
  "detail": "senha alterada com sucesso.",
  "primeiro_acesso": false
}
```

### GET /auth/me/
Retorna dados do usuário autenticado.

Exemplo de resposta:
```json
{
  "login": "admin",
  "primeiro_acesso": false
}
```

### POST /auth/logout/
Encerra a sessão do usuário autenticado.

Exemplo de resposta:
```json
{
  "detail": "logout realizado com sucesso."
}
```

## Fluxo validado na POC
- Login com admin e senha inicial.
- GET /auth/me/ retornando primeiro_acesso = true.
- POST /auth/alterar-senha/ com sucesso.
- GET /auth/me/ retornando primeiro_acesso = false.
- POST /auth/logout/ com sucesso.

## Comandos usados para validação (PowerShell)
```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/auth/login/" -WebSession $session -ContentType "application/json" -Body '{"login":"admin","senha":"bomgosto123"}'

Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/auth/me/" -WebSession $session

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/auth/alterar-senha/" -WebSession $session -ContentType "application/json" -Body '{"senha_atual":"bomgosto123","nova_senha":"BomGosto@2026"}'

Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/auth/me/" -WebSession $session

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/auth/logout/" -WebSession $session
```



