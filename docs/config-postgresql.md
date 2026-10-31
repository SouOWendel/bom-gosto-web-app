# PostgreSQL no desenvolvimento

## Fluxo recomendado: Docker

O projeto usa PostgreSQL 16 no Docker Compose. Para iniciar o banco com o schema atual:

```powershell
docker compose up -d postgres
docker compose ps
```

O banco usado pelo projeto é `db_confeitaria`, com usuário `postgres`, e fica acessível no host pela porta `5432`. O Django usa `postgres` como host quando executado dentro do container backend.

Para consultar o banco sem instalar `psql` no Windows:

```powershell
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "\dt"
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT id_usuario, login, primeiro_acesso FROM usuario;"
```

Os scripts `database/init.sql` e `database/create_schema.sql` são executados automaticamente apenas quando o volume `postgres_data` é criado. Para recriar o banco local:

```powershell
docker compose down -v
docker compose up -d --build
```

Esse comando apaga os dados do banco. Para o fluxo completo, consulte [docker.md](docker.md).

## Alternativa: PostgreSQL instalado no Windows

Use esta seção somente se for executar o Django fora do Docker. Nesse caso, o banco e as tabelas precisam ser criados manualmente e as variáveis `POSTGRES_*` devem apontar para `localhost`.

## 1. Baixar o PostgreSQL

1. Acesse https://www.postgresql.org/download/windows/
2. Clique em **Download the installer** (instalador da EDB).
3. Na tabela de versões, escolha a **18** para **Windows x86-64** e baixe o `.exe`.

## 2. Instalar

Execute o instalador e siga as telas:

1. **Installation Directory:** mantenha o padrão (`C:\Program Files\PostgreSQL\18`).
2. **Select Components:** deixe marcados:
   - PostgreSQL Server
   - pgAdmin
   - Command Line Tools _(necessário para usar o `psql` no terminal)_
3. **Data Directory:** mantenha o padrão.
4. **Password:** defina a senha do superusuário `postgres`. _(Anote essa senha. Ela será pedida no `psql` e na extensão do VS Code)_.
5. **Port:** mantenha **5432**.
6. **Locale:** mantenha o padrão.
7. Clique em **Next** até concluir. Pode desmarcar o Stack Builder no final.

## 3. Configurar o PATH

Para usar o `psql` em qualquer terminal:

1. Aperte a tecla **Windows** e digite `variáveis de ambiente`.
2. Clique em **Editar as variáveis de ambiente do sistema** e depois em **Variáveis de Ambiente...**.
3. Em **Variáveis do sistema**, selecione **Path** e clique em **Editar**.
4. Clique em **Novo** e cole:
   ```
   C:\Program Files\PostgreSQL\18\bin
   ```
5. Clique em **OK** em todas as janelas.
6. **Feche completamente o VS Code (todas as janelas) e abra de novo.**

## 4. Testar

No terminal:

```powershell
psql --version
```

Deve aparecer algo como `psql (PostgreSQL) 18.x`.

Para testar a conexão com o servidor:

```powershell
psql -U postgres -h localhost
```

Digite a senha definida na instalação. Se aparecer o prompt `postgres=#`, está tudo certo. Para sair, use `\q`.

Se o `psql` não for reconhecido, teste o caminho direto:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" --version
```

## 5. Extensão "PostgreSQL" no VS Code

A extensão permite conectar ao banco, navegar pelas tabelas e rodar consultas dentro do VS Code.

### Instalar

1. Abra a aba de extensões (`Ctrl + Shift + X`).
2. Pesquise por **PostgreSQL** e instale a extensão (publicada pela Microsoft).

### Criar a conexão

1. Abra o painel **PostgreSQL** na barra lateral (ícone de elefante).
2. Clique em **Add Connection** (ou no botão **+**).
3. Preencha:

   | Campo                   | Valor                          |
   | ----------------------- | ------------------------------ |
   | **Server name**         | `localhost`                    |
   | **Authentication type** | `Password`                     |
   | **User name**           | `postgres`                     |
   | **Password**            | a senha definida na instalação |

4. Clique em **Test Connection** para validar.
5. Se o teste passar, clique em **Save & Connect**.

A conexão aparecerá no painel, e você poderá expandir os bancos e tabelas, além de abrir um editor de consultas para executar seus scripts `.sql`.

## 6. Scripts SQL de referência

Os scripts de inicialização do PostgreSQL não são repetidos em volumes existentes. Não execute `create_schema.sql` completo em um banco que já contém dados ou tabelas. Tanto `create_schema.sql` quanto `insert_data.sql` são mantidos como referência histórica. Para dados de desenvolvimento do CRUD de pedidos, use o comando `seed_desenvolvimento` descrito no `docs/guia-pedidos-backend.md`.

**Os passos abaixo servem para estudar os scripts SQL em uma instância PostgreSQL separada, fora do Docker Compose da aplicação. Não execute os comandos de criação no banco de aplicação existente.**

### Executando scripts de referência pela extensão PostgreSQL no VS Code

Depois de criar a conexão (etapa 5), qualquer arquivo `.sql` aberto no VS Code pode ser executado usando o perfil conectado. A execução é feita em duas etapas, nesta ordem.

Para executar uma query, é necessário selecionar a opção no canto superior direito _Execute Query (PostgreSQL)_, ou apenas pressionar `Shift + Enter`

### 6.1 Criar um banco separado para consultar os scripts

Esta etapa cria um banco separado para estudo manual na instância PostgreSQL de estudo. O banco `db_confeitaria` do Compose não deve ser usado para executar o schema completo manualmente.

1. Abra o arquivo `create_database.sql`:

```sql
   CREATE DATABASE db_confeitaria;
```

2. Confirme que o arquivo está conectado ao banco padrão `postgres`.
3. Execute o script.
4. No painel do elefante, clique em **Refresh** para o banco `db_confeitaria` aparecer na lista _(Se o banco já existir, o PostgreSQL retorna o erro `already exists`. É inofensivo, basta seguir para a próxima etapa)_.

### 6.2 Consultar o modelo físico SQL

Abra `create_schema.sql` para consultar o modelo físico completo. Em um banco novo e vazio da instância de estudo, o script pode ser executado uma vez para criar as tabelas.
1. Abra o arquivo `create_schema.sql`.
2. **Antes de executar**, confira no editor que a conexão aponta para a instância PostgreSQL separada e que o banco `db_confeitaria` nela está vazio. Não use a conexão do Docker Compose da aplicação.
3. Execute o script.
4. Clique em **Refresh** no painel do elefante e expanda `db_confeitaria` → `Schemas` → `public` → `Tables`. Todas as tabelas devem aparecer.
