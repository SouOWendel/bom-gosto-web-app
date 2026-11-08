# PostgreSQL no desenvolvimento

## Fluxo recomendado: Docker

O projeto usa PostgreSQL no Docker. Para iniciar o banco:

```powershell
docker compose up -d postgres
docker compose ps
```

O banco usado pelo projeto é `db_confeitaria`, com usuário `postgres`, e fica acessível no host pela porta `5432`. O Django usa `postgres` como host quando executado dentro do container backend. Ao iniciar o backend, `python manage.py migrate --noinput` cria e controla as 11 tabelas ativas de aplicação. O Compose `database/create_schema.sql`.

Para consultar o banco sem instalar `psql` no Windows:

```powershell
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "\dt"
docker compose exec -T postgres psql -U postgres -d db_confeitaria -c "SELECT id_usuario, login, primeiro_acesso FROM usuario;"
```

O Compose não executa os scripts SQL de inicialização. `database/create_schema.sql` permanece somente como referência legada e não deve ser executado no banco da aplicação. Para atualizar o schema ativo, inicie o backend para aplicar as migrations. Não remova o volume PostgreSQL. Para o fluxo completo, consulte [docker.md](docker.md).

## Alternativa: PostgreSQL instalado no Windows

Use esta seção somente se for executar o Django fora do Docker. Nesse caso, crie o banco vazio manualmente, configure `POSTGRES_*` para `localhost` e aplique as migrations Django para criar as tabelas ativas.

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

A conexão aparecerá no painel, e você poderá expandir os bancos e tabelas, além de abrir um editor para consultar arquivos `.sql`.

## 6. Scripts SQL de referência legada

`create_schema.sql` e `insert_data.sql` são referências históricas. Não os execute no banco da aplicação: as migrations Django controlam as 11 tabelas ativas do MVP. Para dados de desenvolvimento do CRUD de pedidos, use o comando `seed_desenvolvimento` descrito no `docs/guia-pedidos-backend.md`.

### Consultando scripts de referência pela extensão PostgreSQL no VS Code

Depois de criar a conexão (etapa 5), um arquivo `.sql` pode ser aberto no VS Code para leitura. Não execute o schema legado no banco da aplicação.

Abra `database/create_schema.sql` apenas para consultar o modelo físico legado. Para ver as tabelas do banco ativo, atualize o painel do elefante e expanda `db_confeitaria` → `Schemas` → `public` → `Tables`.
