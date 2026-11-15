# Guia de desenvolvimento com Docker

O ambiente local usa Docker Compose para executar Angular, Django REST e PostgreSQL com hot reload. Execute os comandos a seguir na raiz do repositório.

## Arquitetura

O Compose executa três serviços na mesma rede:

```text
Navegador
  |
  +--> http://localhost:4200 --> frontend (Angular)
                                  |
                                  +--> backend:8000 --> backend (Django)
                                                        |
                                                        +--> postgres:5432 --> postgres
```

O navegador acessa `localhost`, mas o proxy do Angular encaminha `/api` para `http://backend:8000` dentro da rede Docker. O Django acessa o banco pelo host `postgres`, não por `localhost`.

## Iniciar o ambiente

```powershell
docker compose up -d --build
docker compose ps
```

O serviço `postgres` possui healthcheck. O `backend` só inicia depois que o banco estiver saudável e executa automaticamente:

```text
python manage.py migrate --noinput
python manage.py runserver 0.0.0.0:8000
```

Abra `http://localhost:4200` para usar o frontend ou `http://localhost:8000` para acessar a API diretamente.

As migrations Django criam e controlam as 11 tabelas ativas de aplicação. O Compose não executa `database/create_schema.sql`.

## Migrations

Após alterar modelos Django, crie e aplique os arquivos de migration:

```powershell
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

O `migrate --noinput` é automático ao iniciar o backend. O `makemigrations` não é automático: os arquivos gerados devem ser revisados e versionados.

O `migrate` automático só roda quando o container do backend inicia. Depois de `git pull` ou de trocar de branch com os containers já em execução, aplique as migrations novas:

```powershell
docker compose exec backend python manage.py migrate
```

## Banco de dados

Verificar a conexão e os usuários:

```powershell
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT current_database(), current_user;"
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT id_usuario, login, primeiro_acesso FROM usuario;"
```

### Consultar dados persistidos

Exemplos de queries para confirmar que as alterações foram gravadas no PostgreSQL:

```powershell
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT * FROM pedido ORDER BY id_pedido DESC LIMIT 10;"

docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT * FROM receita ORDER BY id_receita DESC LIMIT 10;"

docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT * FROM ingrediente ORDER BY id_ingrediente DESC LIMIT 10;"

docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT * FROM estoque ORDER BY id_estoque DESC LIMIT 10;"
```

Para conferir um registro específico, filtre pelo identificador. Substitua `1` pelo ID exibido pela aplicação ou pela API:

```powershell
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT * FROM ingrediente WHERE id_ingrediente = 1;"
```

Verificar a conexão usando as configurações do Django:

```powershell
docker compose exec -T backend python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Conexao Django OK')"
```

O banco ativo é preparado e atualizado pelas migrations Django. O script `database/create_schema.sql` não é executado pelo Compose. `create_schema.sql` permanece somente como referência legada. Não remova o volume para atualizar o schema: isso apaga os dados persistidos.

## Diagnóstico

```powershell
docker compose ps
docker compose logs -f postgres backend frontend
```

Erros comuns:

- `connection refused` em `localhost`: confira se o Django está sendo executado dentro do container e se `POSTGRES_HOST=postgres` está configurado.
- `column ... does not exist` (erro 500 nas telas) depois de atualizar o código: há migration nova ainda não aplicada. Rode `docker compose exec backend python manage.py migrate`.
- `relation "usuario" does not exist`: confira os logs do backend e o estado das migrations. Não execute `database/create_schema.sql` nem remova o volume como procedimento de recuperação do banco ativo.
- `ECONNREFUSED 127.0.0.1:8000` no frontend: o proxy deve usar `http://backend:8000`, pois `127.0.0.1` dentro do frontend aponta para o próprio container.
- `DisallowedHost`: confirme que `backend` está em `ALLOWED_HOSTS` no Django.

## Parar o ambiente

```powershell
docker compose down
```
