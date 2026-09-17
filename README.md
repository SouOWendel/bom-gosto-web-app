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

---

## POC de Autenticação (Back-end)

Implementação inicial do fluxo de autenticação no back-end para prova de conceito, sem integração com API externa e sem alterações no front-end.

### Regras de negócio atendidas
- Login com usuário e senha.
- Identificação de primeiro acesso.
- Troca obrigatória de senha no primeiro acesso.
- Logout seguro.
- Sessão persistente no navegador até logout manual ou expiração configurada.

### Endpoints
Base local: `http://127.0.0.1:8000/api`

- `POST /auth/login/`
- `POST /auth/alterar-senha/`
- `GET /auth/me/`
- `POST /auth/logout/`

### Execução rápida (back-end)
```bash
cd apps/backend
python -m venv .venv
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

Para detalhes técnicos (payloads, respostas e fluxo de validação), consulte [`docs/auth-poc.md`](docs/auth-poc.md).


