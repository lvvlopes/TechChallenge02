# =============================================================================
# deploy_azure.ps1
# Script de deploy para Azure Container Apps — Windows PowerShell
#
# Pré-requisitos:
#   1. Docker Desktop instalado e rodando
#   2. Azure CLI instalado: https://aka.ms/installazurecliwindows
#   3. Conta Azure com créditos disponíveis
#
# Uso (no PowerShell, dentro da pasta do projeto):
#   .\deploy_azure.ps1
#
# Se der erro de permissão:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# =============================================================================

$ErrorActionPreference = "Stop"

# ── Configurações — EDITE AQUI ────────────────────────────────────────────────
$RESOURCE_GROUP    = "vrp-rmsp-rg"
$LOCATION          = "brazilsouth"
$ACR_NAME          = "vrprmspcr"
$APP_NAME          = "vrp-rmsp"
$ENVIRONMENT_NAME  = "vrp-rmsp-env"
$IMAGE_TAG         = "latest"

# ── Lê a chave OpenAI do .env ─────────────────────────────────────────────────
$OPENAI_KEY = ""
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Encoding UTF8
    foreach ($line in $envContent) {
        $line = $line.Trim()
        if ($line -match "^OPENAI_API_KEY=(.+)$") {
            $OPENAI_KEY = $matches[1].Trim()
        }
    }
}

# ── Funções auxiliares ────────────────────────────────────────────────────────
function Step($msg) {
    Write-Host "`n[$([datetime]::Now.ToString('HH:mm:ss'))] $msg" -ForegroundColor Cyan
}
function Ok($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  ⚠ $msg" -ForegroundColor Yellow }

# ── Validações ────────────────────────────────────────────────────────────────
Step "Verificando pré-requisitos..."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker não encontrado. Instale em https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
    exit 1
}
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "Azure CLI não encontrado. Instale em https://aka.ms/installazurecliwindows" -ForegroundColor Red
    exit 1
}

Ok "Docker e Azure CLI encontrados."

if (-not $OPENAI_KEY) {
    Warn "OPENAI_API_KEY não encontrada no .env — o relatório LLM não funcionará no Azure."
}

# ── Login no Azure ────────────────────────────────────────────────────────────
Step "Verificando login no Azure..."
$accountJson = az account show 2>$null
if (-not $accountJson) {
    Write-Host "  Abrindo login no Azure..." -ForegroundColor Yellow
    az login
}
Ok "Logado no Azure."
az account show --query "{Nome:name, ID:id}" -o table

# ── Grupo de recursos ─────────────────────────────────────────────────────────
Step "Criando grupo de recursos: $RESOURCE_GROUP..."
az group create `
    --name $RESOURCE_GROUP `
    --location $LOCATION `
    --output none
Ok "Grupo de recursos criado."

# ── Azure Container Registry ──────────────────────────────────────────────────
Step "Criando Container Registry: $ACR_NAME..."
az acr create `
    --resource-group $RESOURCE_GROUP `
    --name $ACR_NAME `
    --sku Basic `
    --admin-enabled true `
    --output none
Ok "Container Registry criado."

$ACR_LOGIN_SERVER = az acr show --name $ACR_NAME --query loginServer -o tsv
$ACR_PASSWORD     = az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv
$IMAGE_FULL       = "$ACR_LOGIN_SERVER/${APP_NAME}:$IMAGE_TAG"

Write-Host "  Registry: $ACR_LOGIN_SERVER" -ForegroundColor Gray

# ── Build da imagem Docker ────────────────────────────────────────────────────
Step "Fazendo build da imagem Docker..."
docker build -t $IMAGE_FULL .
Ok "Imagem criada: $IMAGE_FULL"

# ── Push para o ACR ───────────────────────────────────────────────────────────
Step "Fazendo push para o Azure Container Registry..."
docker login $ACR_LOGIN_SERVER --username $ACR_NAME --password $ACR_PASSWORD
docker push $IMAGE_FULL
Ok "Imagem publicada no registry."

# ── Container Apps Environment ────────────────────────────────────────────────
Step "Instalando extensão Container Apps..."
$ErrorActionPreference = "Continue"
az extension add --name containerapp --upgrade --output none 2>&1 | Out-Null
az provider register --namespace Microsoft.App --output none 2>&1 | Out-Null
az provider register --namespace Microsoft.OperationalInsights --output none 2>&1 | Out-Null
$ErrorActionPreference = "Stop"
Ok "Extensões registradas."

Step "Criando ambiente Container Apps: $ENVIRONMENT_NAME..."
az containerapp env create `
    --name $ENVIRONMENT_NAME `
    --resource-group $RESOURCE_GROUP `
    --location $LOCATION `
    --output none
Ok "Ambiente criado."

# ── Deploy do Container App ───────────────────────────────────────────────────
Step "Fazendo deploy do Container App: $APP_NAME..."

# Monta variáveis de ambiente
$envVars = "PYTHONUNBUFFERED=1"
if ($OPENAI_KEY) {
    $envVars = "$envVars OPENAI_API_KEY=$OPENAI_KEY"
}

az containerapp create `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --environment $ENVIRONMENT_NAME `
    --image $IMAGE_FULL `
    --registry-server $ACR_LOGIN_SERVER `
    --registry-username $ACR_NAME `
    --registry-password $ACR_PASSWORD `
    --target-port 8000 `
    --ingress external `
    --min-replicas 1 `
    --max-replicas 3 `
    --cpu 1.0 `
    --memory 2.0Gi `
    --env-vars $envVars `
    --output none

Ok "Container App deployado."

# ── URL pública ───────────────────────────────────────────────────────────────
$APP_URL = az containerapp show `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query "properties.configuration.ingress.fqdn" `
    -o tsv

# ── Resultado ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✓ DEPLOY CONCLUÍDO COM SUCESSO!"                  -ForegroundColor Green
Write-Host "══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  🌐 URL pública : https://$APP_URL"               -ForegroundColor Cyan
Write-Host "  📊 Swagger UI  : https://$APP_URL/docs"          -ForegroundColor Cyan
Write-Host ""
Write-Host "  Para ver logs em tempo real:"                     -ForegroundColor Gray
Write-Host "  az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Para atualizar após mudanças no código:"         -ForegroundColor Gray
Write-Host "  .\update_azure.ps1"                              -ForegroundColor Yellow
Write-Host ""
