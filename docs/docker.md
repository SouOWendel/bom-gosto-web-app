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
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Abra `http://localhost:4200` para usar o frontend ou `http://localhost:8000` para acessar a API diretamente.

## Migrations

Após alterar modelos Django, crie e aplique os arquivos de migration:

```powershell
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

O `migrate` é automático ao iniciar o backend. O `makemigrations` não é automático: os arquivos gerados devem ser revisados e versionados.

## Banco de dados

Em um volume novo, o PostgreSQL executa, nesta ordem, `database/init.sql` e `database/create_schema.sql`. O segundo cria as tabelas de domínio, incluindo `usuario`. O modelo Django `Usuario` usa `managed = False`, portanto o Django não cria nem altera essa tabela.

Verificar a conexão e os usuários:

```powershell
docker compose exec -T postgres psql -U postgres -d bom_gosto_db -c "SELECT current_database(), current_user;"
docker compose exec -T postgres psql -U postgres -d bom_gosto_db -c "SELECT id_usuario, login, primeiro_acesso FROM usuario;"
```

Verificar a conexão usando as configurações do Django:

```powershell
docker compose exec -T backend python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Conexao Django OK')"
```

Os scripts de `/docker-entrypoint-initdb.d/` só são executados quando o volume é criado. Para reconstruir o banco local do zero:

```powershell
docker compose down -v
docker compose up -d --build
```

Esse procedimento apaga os dados do volume `postgres_data`.

## Diagnóstico

```powershell
docker compose ps
docker compose logs -f postgres backend frontend
```

Erros comuns:

- `connection refused` em `localhost`: confira se o Django está sendo executado dentro do container e se `POSTGRES_HOST=postgres` está configurado.
- `relation "usuario" does not exist`: o schema não foi aplicado ao volume atual. Recrie o volume apenas se puder apagar os dados, ou aplique `database/create_schema.sql` manualmente.
- `ECONNREFUSED 127.0.0.1:8000` no frontend: o proxy deve usar `http://backend:8000`, pois `127.0.0.1` dentro do frontend aponta para o próprio container.
- `DisallowedHost`: confirme que `backend` está em `ALLOWED_HOSTS` no Django.

## Parar o ambiente

```powershell
docker compose down
```
