# 🎂 Confeitaria Bom Gosto — Web App

Sistema integrado de **Comércio Conversacional e Gestão Operacional (SaaS All-in-One)** desenvolvido para a Confeitaria Bom Gosto. O projeto centraliza a gestão de pedidos via WhatsApp, catálogo digital, agenda de entregas, controle financeiro, estoque de produtos e cálculo de receitas de produção.

---

## 📐 Arquitetura do Sistema

O projeto é estruturado como um **Monorepo** dividido em dois domínios principais:

- **Mega-Componente Administrativo:** Responsável pela gestão direta de Pedidos (Internos/Externos, Vitrine/Personalizado), Agenda de entregas e Livro de Finanças (sinais e quitações)[cite: 1].
- **Mega-Componente Fábrica:** Responsável pela gestão de Estoque, Inventário de matérias-primas, cálculo de custos de Produção e geração de Relatórios[cite: 1].

---

## 🛠️ Tecnologias e Ferramentas

- **Front-End:** Angular (PWA / UI Mobile-First)[cite: 1]
- **Back-End:** Python com Django + Django REST Framework[cite: 1]
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
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
docker compose exec -T postgres psql -U postgres -d bom_gosto_db
```

Para parar os containers sem apagar o banco:

```powershell
docker compose down
```

Para apagar também o volume do PostgreSQL e recriar o banco do zero:

```powershell
docker compose down -v
docker compose up -d --build
```

O segundo comando apaga os dados locais do PostgreSQL. Consulte os guias abaixo para os fluxos específicos:

- [Guia do Docker](docs/docker.md): inicialização, migrations, banco e diagnóstico.
- [POC de autenticação](docs/auth-poc.md): cadastro de teste, login, sessão e troca de senha.
- [Guia do back-end de pedidos](docs/guia-pedidos-backend.md): testar a API de pedidos autenticada.
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
