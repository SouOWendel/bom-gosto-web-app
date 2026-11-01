# 🎂 Confeitaria Bom Gosto — Web App

Sistema de gestão operacional da Confeitaria Bom Gosto, com backend Django para pedidos, receitas, produção, inventário, estoque e autenticação. Agenda, Relatórios e Finanças permanecem planejados para etapas posteriores.

---

## 📐 Arquitetura do Sistema

O projeto é estruturado como um **Monorepo** dividido em dois domínios principais:

- **Pedidos:** pedidos internos e externos, com análise de disponibilidade, receitas e ingredientes.
- **Fábrica:** receitas, produção por pedido, inventário de matérias-primas e lotes de produtos prontos.
- **Usuário:** sessão autenticada, troca obrigatória de senha no primeiro acesso e logout.
- **Etapas posteriores:** Agenda, Relatórios e Finanças.

---

## 🛠️ Tecnologias e Ferramentas

- **Front-End:** Angular (em implementação posterior)
- **Back-End:** Python com Django + Django REST Framework
- **Banco de Dados:** PostgreSQL[cite: 1]
- **Infraestrutura & DevOps:** Docker, Docker Compose, GitHub Actions (CI/CD)[cite: 1]
- **Qualidade de Código & Automação:** Husky, Commitlint (Conventional Commits), Prettier, `openapi-typescript`[cite: 1]

## 🚀 Inicialização do desenvolvimento

Pré-requisitos:

- Docker Desktop em execução;
- Docker Compose disponível no terminal;
- Node.js e npm apenas para executar ferramentas do monorepo fora dos containers.

Na raiz do projeto, inicie o ambiente completo:

```powershell
docker compose up -d --build
```

O Compose inicia o PostgreSQL, cria o schema inicial em um banco novo, aplica as migrations do Django e sobe os servidores:

- Frontend: http://localhost:4200
- Backend: http://localhost:8000
- PostgreSQL: `localhost:5432`

Comandos úteis:

```powershell
docker compose ps
docker compose logs -f backend frontend
docker compose exec backend python manage.py migrate
docker compose exec -T postgres psql -U postgres -d db_confeitaria
```

Para parar os containers sem apagar o banco:

```powershell
docker compose down
```

Para preservar o banco atual, não remova o volume PostgreSQL ao atualizar os serviços. O schema de referência em `database/create_schema.sql` serve para instalações novas; não o execute sobre um banco existente nem gere migrations para os models de tabelas preexistentes. Consulte os guias abaixo para os fluxos específicos:

- [Guia do Docker](docs/docker.md): inicialização, migrations, banco e diagnóstico.
- [POC de autenticação](docs/auth-poc.md): cadastro de teste, login, sessão e troca de senha.
- [Guia do back-end de pedidos](docs/guia-pedidos-backend.md): testar a API de pedidos autenticada.
- [Guia do back-end de inventário](docs/guia-inventario-backend.md): testar a API de ingredientes.
- [Guia do back-end de estoque](docs/guia-estoque-backend.md): testar a API de produtos prontos em estoque.
- [Contratos da API operacional](docs/api-fluxos-operacionais.md): rotas, payloads, respostas e regras dos fluxos de pedido e produção.
- [Configuração do PostgreSQL](docs/config-postgresql.md): acesso ao banco pelo terminal ou pelo VS Code.

---

## 📂 Estrutura do Repositório

```text
bom-gosto-web-app/
├── .github/
│   └── workflows/          # Pipelines de CI/CD (Frontend e Backend)
├── apps/
│   ├── frontend/           # Aplicação Angular (PWA / UI Mobile-First)
│   └── backend/            # API REST Django (Módulos Administrativo e Fábrica)
├── database/               # Scripts de inicialização do PostgreSQL
├── .commitlintrc.json      # Regras do Commitlint
├── .husky/                 # Hooks do Git (commit-msg, pre-commit)
├── .prettierrc             # Configuração de formatação do Prettier
├── docker-compose.yml      # Ambiente orquestrado com Docker
├── Makefile                # Atalhos para comandos do projeto
├── CONTRIBUTING.md         # Guia de contribuição e convenções do Git
└── README.md
```
