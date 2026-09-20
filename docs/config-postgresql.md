# Instalando o PostgreSQL 18 no Windows e conectando pelo VS Code

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
   - Command Line Tools *(necessário para usar o `psql` no terminal)*
3. **Data Directory:** mantenha o padrão.
4. **Password:** defina a senha do superusuário `postgres`. *(Anote essa senha. Ela será pedida no `psql` e na extensão do VS Code)*.
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

   | Campo | Valor |
   |---|---|
   | **Server name** | `localhost` |
   | **Authentication type** | `Password` |
   | **User name** | `postgres` |
   | **Password** | a senha definida na instalação |

4. Clique em **Test Connection** para validar.
5. Se o teste passar, clique em **Save & Connect**.

A conexão aparecerá no painel, e você poderá expandir os bancos e tabelas, além de abrir um editor de consultas para executar seus scripts `.sql`.

## 6. Executando os scripts pela extensão "PostgreSQL" no VS Code

Depois de criar a conexão (etapa 5), qualquer arquivo `.sql` aberto no VS Code pode ser executado usando o perfil conectado. A execução é feita em duas etapas, nesta ordem.

Para executar uma query, é necessário selecionar a opção no canto superior direito *Execute Query (PostgreSQL)*, ou apenas pressionar `Shift + Enter` 

### 6.1 Criar o banco de dados

1. Abra o arquivo `create_database.sql`:
```sql
   CREATE DATABASE db_confeitaria;
```
2. Confirme que o arquivo está conectado ao banco padrão `postgres`.
3. Execute o script.
4. No painel do elefante, clique em **Refresh** para o banco `db_confeitaria` aparecer na lista *(Se o banco já existir, o PostgreSQL retorna o erro `already exists`. É inofensivo, basta seguir para a próxima etapa)*.

### 6.2 Criar as tabelas (schema)

1. Abra o arquivo `create_schema.sql`.
2. **Antes de executar**, confira no editor qual banco está selecionado para o arquivo. Ele deve ser `db_confeitaria`. *(Se estiver em `postgres`, as tabelas serão criadas no banco errado. Troque a seleção para `db_confeitaria`,ou crie uma nova conexão apontando para ele)*
3. Execute o script.
4. Clique em **Refresh** no painel do elefante e expanda `db_confeitaria` → `Schemas` → `public` → `Tables`. Todas as tabelas devem aparecer.