#!/usr/bin/env bash
# Atualiza a aplicação no servidor EC2. Executado pelo GitHub Actions via SSM Run Command.
# Uso: deploy.sh <registro-ecr> <tag-da-imagem>
set -euo pipefail

REGISTRY="$1"
TAG="$2"
REGION="${AWS_REGION:-us-east-2}"
APP_DIR=/opt/bom-gosto
PARAM_PATH=/bom-gosto/prod

cd "$APP_DIR"

# Monta o .env a partir do Parameter Store (segredos criptografados ficam só no servidor).
umask 077
aws ssm get-parameters-by-path --region "$REGION" --path "$PARAM_PATH" --with-decryption \
  --query 'Parameters[].[Name,Value]' --output text \
  | while IFS=$'\t' read -r name value; do printf '%s=%s\n' "${name#"$PARAM_PATH/"}" "$value"; done > .env.new
{
  echo "BACKEND_IMAGE=${REGISTRY}/bom-gosto/backend:${TAG}"
  echo "FRONTEND_IMAGE=${REGISTRY}/bom-gosto/frontend:${TAG}"
} >> .env.new
mv .env.new .env

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

docker compose -f docker-compose.prod.yml pull --quiet
docker compose -f docker-compose.prod.yml up -d postgres
docker compose -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# Espera o Nginx responder e confere que o Django atende pela rede interna.
saude() { docker compose -f docker-compose.prod.yml exec -T frontend wget -qO- http://127.0.0.1/healthz; }
for _ in $(seq 1 30); do
  if saude >/dev/null 2>&1; then break; fi
  sleep 2
done
saude || { docker compose -f docker-compose.prod.yml logs --tail 50 frontend; exit 1; }
docker compose -f docker-compose.prod.yml exec -T backend \
  python -c "import os, urllib.request; host = os.environ['DJANGO_ALLOWED_HOSTS'].split(',')[0]; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/api/auth/csrf/', headers={'Host': host}))" \
  || { docker compose -f docker-compose.prod.yml logs --tail 50 backend; exit 1; }

docker image prune -af --filter "until=168h" >/dev/null || true
docker compose -f docker-compose.prod.yml ps
echo "Deploy da versão ${TAG} concluído."
