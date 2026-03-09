#!/usr/bin/env bash
# =============================================================================
# update_azure.sh
# Atualiza o Container App após mudanças no código.
# Mais rápido que o deploy_azure.sh — não recria os recursos Azure.
#
# Uso: bash update_azure.sh
# =============================================================================

set -e

# ── Mesmas configurações do deploy_azure.sh ───────────────────────────────────
RESOURCE_GROUP="vrp-rmsp-rg"
ACR_NAME="vrprmspcr"
APP_NAME="vrp-rmsp"
IMAGE_TAG="latest"

BLUE='\033[0;34m'; GREEN='\033[0;32m'; NC='\033[0m'
step() { echo -e "\n${BLUE}[$(date +%H:%M:%S)]${NC} ${GREEN}$1${NC}"; }

# ── Build + Push ──────────────────────────────────────────────────────────────
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)
IMAGE_FULL="$ACR_LOGIN_SERVER/$APP_NAME:$IMAGE_TAG"

step "Build da nova imagem..."
docker build -t "$IMAGE_FULL" .

step "Push para o Container Registry..."
docker login "$ACR_LOGIN_SERVER" --username "$ACR_NAME" --password "$ACR_PASSWORD"
docker push "$IMAGE_FULL"

step "Atualizando Container App..."
az containerapp update \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "$IMAGE_FULL" \
    --output none

APP_URL=$(az containerapp show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo -e "${GREEN}✓ Atualização concluída!${NC}"
echo -e "  🌐 https://$APP_URL"
