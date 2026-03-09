# =============================================================================
# update_azure.ps1
# Atualiza o Container App após mudanças no código.
# Mais rápido que o deploy_azure.ps1 — não recria os recursos Azure.
#
# Uso: .\update_azure.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# ── Mesmas configurações do deploy_azure.ps1 ──────────────────────────────────
$RESOURCE_GROUP = "vrp-rmsp-rg"
$ACR_NAME       = "vrprmspcr"
$APP_NAME       = "vrp-rmsp"
$IMAGE_TAG      = "latest"

function Step($msg) {
    Write-Host "`n[$([datetime]::Now.ToString('HH:mm:ss'))] $msg" -ForegroundColor Cyan
}

# ── Build + Push ──────────────────────────────────────────────────────────────
$ACR_LOGIN_SERVER = az acr show --name $ACR_NAME --query loginServer -o tsv
$ACR_PASSWORD     = az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv
$IMAGE_FULL       = "$ACR_LOGIN_SERVER/${APP_NAME}:$IMAGE_TAG"

Step "Build da nova imagem..."
docker build -t $IMAGE_FULL .

Step "Push para o Container Registry..."
docker login $ACR_LOGIN_SERVER --username $ACR_NAME --password $ACR_PASSWORD
docker push $IMAGE_FULL

Step "Atualizando Container App..."
az containerapp update `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --image $IMAGE_FULL `
    --output none

$APP_URL = az containerapp show `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query "properties.configuration.ingress.fqdn" `
    -o tsv

Write-Host ""
Write-Host "  ✓ Atualização concluída!" -ForegroundColor Green
Write-Host "  🌐 https://$APP_URL"      -ForegroundColor Cyan
