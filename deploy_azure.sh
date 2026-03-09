#!/usr/bin/env bash
# =============================================================================
# deploy_azure.sh
# Script de deploy para Azure Container Apps
#
# Pré-requisitos:
#   1. Docker Desktop instalado e rodando
#   2. Azure CLI instalado: https://learn.microsoft.com/pt-br/cli/azure/install-azure-cli
#   3. Conta Azure com créditos disponíveis
#
# Uso:
#   Windows (Git Bash / WSL):  bash deploy_azure.sh
#   Linux/macOS:               ./deploy_azure.sh
#
# Tempo estimado: 5-10 minutos na primeira vez
# =============================================================================

set -e  # Para imediatamente se qualquer comando falhar

# ── Configurações — EDITE AQUI ────────────────────────────────────────────────
RESOURCE_GROUP="vrp-rmsp-rg"           # Nome do grupo de recursos Azure
LOCATION="brazilsouth"                  # Região (brazilsouth = São Paulo)
ACR_NAME="vrprmspcr"                   # Nome do Container Registry (único no Azure, só letras/números)
APP_NAME="vrp-rmsp"                    # Nome do Container App (vira parte da URL)
ENVIRONMENT_NAME="vrp-rmsp-env"        # Nome do ambiente do Container Apps
IMAGE_TAG="latest"                     # Tag da imagem Docker

# A chave OpenAI será lida do seu .env local e passada como secret no Azure
OPENAI_KEY=$(grep OPENAI_API_KEY .env 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')

# ── Cores para output ─────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

step() { echo -e "\n${BLUE}[$(date +%H:%M:%S)]${NC} ${GREEN}$1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
err()  { echo -e "${RED}✗ $1${NC}"; exit 1; }

# ── Validações iniciais ───────────────────────────────────────────────────────
step "Verificando pré-requisitos..."

command -v docker &>/dev/null || err "Docker não encontrado. Instale em https://www.docker.com/products/docker-desktop/"
command -v az     &>/dev/null || err "Azure CLI não encontrado. Instale em https://aka.ms/installazurecliwindows"

if [ -z "$OPENAI_KEY" ]; then
    warn "OPENAI_API_KEY não encontrada no .env — o relatório LLM não funcionará no Azure."
    warn "Adicione OPENAI_API_KEY=sk-... no seu arquivo .env antes de fazer o deploy."
fi

# ── Login no Azure ────────────────────────────────────────────────────────────
step "Fazendo login no Azure..."
az account show &>/dev/null || az login

echo "Assinatura ativa:"
az account show --query "{Nome:name, ID:id}" -o table

# ── Grupo de recursos ─────────────────────────────────────────────────────────
step "Criando grupo de recursos: $RESOURCE_GROUP..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none

# ── Azure Container Registry ──────────────────────────────────────────────────
step "Criando Container Registry: $ACR_NAME..."
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true \
    --output none

# Obtém credenciais do ACR
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

echo "Registry: $ACR_LOGIN_SERVER"

# ── Build da imagem Docker ────────────────────────────────────────────────────
step "Fazendo build da imagem Docker..."
IMAGE_FULL="$ACR_LOGIN_SERVER/$APP_NAME:$IMAGE_TAG"

docker build -t "$IMAGE_FULL" .

# ── Push para o ACR ───────────────────────────────────────────────────────────
step "Fazendo push da imagem para o Azure Container Registry..."
docker login "$ACR_LOGIN_SERVER" \
    --username "$ACR_NAME" \
    --password "$ACR_PASSWORD"

docker push "$IMAGE_FULL"

# ── Container Apps Environment ────────────────────────────────────────────────
step "Instalando extensão Container Apps (se necessário)..."
az extension add --name containerapp --upgrade --output none 2>/dev/null || true
az provider register --namespace Microsoft.App --output none 2>/dev/null || true
az provider register --namespace Microsoft.OperationalInsights --output none 2>/dev/null || true

step "Criando ambiente Container Apps: $ENVIRONMENT_NAME..."
az containerapp env create \
    --name "$ENVIRONMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none

# ── Deploy do Container App ───────────────────────────────────────────────────
step "Fazendo deploy do Container App: $APP_NAME..."

# Monta as variáveis de ambiente
ENV_VARS="PYTHONUNBUFFERED=1"
if [ -n "$OPENAI_KEY" ]; then
    ENV_VARS="$ENV_VARS OPENAI_API_KEY=$OPENAI_KEY"
fi

az containerapp create \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENVIRONMENT_NAME" \
    --image "$IMAGE_FULL" \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_NAME" \
    --registry-password "$ACR_PASSWORD" \
    --target-port 8000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 1.0 \
    --memory 2.0Gi \
    --env-vars $ENV_VARS \
    --output none

# ── Obtém a URL pública ───────────────────────────────────────────────────────
step "Obtendo URL pública..."
APP_URL=$(az containerapp show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" \
    -o tsv)

# ── Resultado ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ DEPLOY CONCLUÍDO COM SUCESSO!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  🌐 URL pública: ${BLUE}https://$APP_URL${NC}"
echo -e "  📊 Swagger UI:  ${BLUE}https://$APP_URL/docs${NC}"
echo ""
echo -e "  Para ver logs em tempo real:"
echo -e "  ${YELLOW}az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow${NC}"
echo ""
echo -e "  Para atualizar após mudanças no código:"
echo -e "  ${YELLOW}bash deploy_azure.sh${NC}  (reusa todos os recursos existentes)"
echo ""
