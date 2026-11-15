# Deploy na AWS

Este documento explica como o Bom Gosto roda em produção na AWS e como o deploy contínuo funciona.

## Arquitetura

```
Navegador ──HTTPS──▶ CloudFront ──HTTP (só IPs do CloudFront)──▶ EC2 t4g.small (us-east-2)
                     (xxxx.cloudfront.net)                        └─ Docker Compose
                                                                     ├─ frontend: Nginx + Angular (porta 80)
                                                                     │    └─ /api/* ──▶ backend
                                                                     ├─ backend: Django + Gunicorn
                                                                     └─ postgres: PostgreSQL 16 (volume em disco)
```

- **CloudFront**: entrega o site com HTTPS no endereço `https://xxxx.cloudfront.net`, sem precisar de domínio
  próprio. Arquivos do Angular com hash no nome ficam em cache; `/api/*` nunca é cacheado.
- **EC2**: um único servidor ARM64 (Graviton) com Amazon Linux 2023. Não tem SSH aberto; o acesso é pelo
  **SSM Session Manager**. O security group só aceita a porta 80 vinda da lista gerenciada de IPs do
  CloudFront. Além disso, o Nginx exige o cabeçalho secreto `X-Origin-Verify`, que só a nossa distribuição envia.
- **Banco**: PostgreSQL em container, com dados no disco EBS criptografado. O AWS Data Lifecycle Manager tira
  um **snapshot diário às 06:00 UTC** e mantém os 7 mais recentes.
- **Segredos**: `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` e `ORIGIN_VERIFY_SECRET` ficam no **SSM Parameter Store**
  (SecureString) em `/bom-gosto/prod/`. O servidor monta o `.env` a cada deploy; nada disso vai para o Git.
- **Imagens**: repositórios ECR `bom-gosto/backend` e `bom-gosto/frontend` (mantêm as 10 últimas).

Toda a infraestrutura está em [`infra/aws/bom-gosto.yml`](../infra/aws/bom-gosto.yml) (stack CloudFormation
`bom-gosto-prod`).

## Deploy contínuo

1. Um push na `main` roda o CI ([`ci.yml`](../.github/workflows/ci.yml)): commitlint e testes do backend e do frontend.
2. Se tudo passar, o CI chama [`deploy.yml`](../.github/workflows/deploy.yml), que:
   - gera as imagens ARM64 e envia para o ECR com a tag do commit;
   - roda [`deploy/deploy.sh`](../deploy/deploy.sh) no servidor via **SSM Run Command**: baixa as imagens, aplica
     as migrations e sobe a nova versão;
   - testa o site pelo CloudFront.
3. O deploy também pode ser disparado manualmente em **Actions → Deploy AWS → Run workflow**, escolhendo a branch.

**Rollback**: rode o workflow manualmente a partir do commit anterior (ou reverta o commit na `main`).

### Credenciais do GitHub Actions

O plano gratuito da nova experiência da AWS bloqueia provedores OIDC, então o GitHub Actions usa a chave de
acesso do usuário IAM `bom-gosto-github-deploy`, que só pode enviar imagens para os dois repositórios ECR, executar
comandos no servidor de produção e ler as saídas da stack.

A chave fica nos secrets do repositório: `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY`.
**Troque a chave a cada 90 dias** (IAM → Usuários → `bom-gosto-github-deploy` → Credenciais de segurança).

## Operação

- **Criar o primeiro usuário** (a senha provisória aparece uma única vez):
  ```bash
  sudo docker compose -f /opt/bom-gosto/docker-compose.prod.yml exec backend python manage.py criar_usuario_inicial <login>
  ```
  Rode pelo Session Manager: console do EC2 → instância `bom-gosto-prod` → **Conectar** → **Session Manager**.
- **Logs**: `sudo docker compose -f /opt/bom-gosto/docker-compose.prod.yml logs -f backend`
- **Restaurar backup**: crie um volume a partir do snapshot desejado (EC2 → Snapshots) e troque o volume raiz
  da instância.

## Custos (aproximados, região us-east-2)

| Recurso                          | Custo mensal          |
| -------------------------------- | --------------------- |
| EC2 t4g.small                    | ~US$ 12               |
| IP público (Elastic IP)          | ~US$ 3,60             |
| Disco gp3 20 GB + snapshots      | ~US$ 2                |
| CloudFront, ECR, Parameter Store | centavos neste volume |
| **Total**                        | **~US$ 18**           |

No plano gratuito, isso é descontado dos créditos do projeto. Acompanhe em **AWS Settings → Billing**.

## Remover tudo

Apagar a stack remove servidor, banco, CloudFront, ECR e o usuário de deploy (**os dados do banco são perdidos**;
os snapshots ficam e podem ser apagados em EC2 → Snapshots):

1. No IAM, apague a chave de acesso do usuário `bom-gosto-github-deploy`.
2. No CloudFormation, apague a stack `bom-gosto-prod`.
3. No Systems Manager → Parameter Store, apague os parâmetros em `/bom-gosto/prod/`.
