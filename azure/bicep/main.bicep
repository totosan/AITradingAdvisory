// MagenticOne Infrastructure - Azure Bicep Template
// Deploys: Container Apps Environment, Backend API, Frontend Web UI
//
// Usage:
//   az deployment sub create \
//     --location swedencentral \
//     --template-file main.bicep \
//     --parameters appName=magentic-one

targetScope = 'subscription'

// ============================================================================
// Parameters
// ============================================================================

@description('Application name prefix for all resources')
param appName string = 'magentic-one'

@description('Azure region for deployment')
param location string = 'swedencentral'

@description('Container image tag')
param imageTag string = 'latest'

@description('Azure Container Registry name')
param acrName string = '${replace(appName, '-', '')}acr'

@description('LLM Provider (azure or ollama)')
@allowed(['azure', 'ollama'])
param llmProvider string = 'azure'

@description('Azure OpenAI endpoint URL')
@secure()
param azureOpenAIEndpoint string = ''

@description('Azure OpenAI API key')
@secure()
param azureOpenAIApiKey string = ''

@description('Azure OpenAI deployment name')
param azureOpenAIDeployment string = 'gpt-4o'

@description('Enable Bitget exchange integration')
param enableBitget bool = false

@secure()
param bitgetApiKey string = ''

@secure()
param bitgetApiSecret string = ''

@secure()
param bitgetPassphrase string = ''

// ============================================================================
// Variables
// ============================================================================

var resourceGroupName = 'rg-${appName}'
var logAnalyticsName = 'log-${appName}'
var containerEnvName = 'cae-${appName}'
var backendAppName = 'ca-${appName}-backend'
var frontendAppName = 'ca-${appName}-frontend'

// ============================================================================
// Resource Group
// ============================================================================

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
  tags: {
    app: appName
    environment: 'production'
  }
}

// ============================================================================
// Azure Container Registry
// ============================================================================

module acr 'modules/acr.bicep' = {
  name: 'acr-deployment'
  scope: rg
  params: {
    name: acrName
    location: location
  }
}

// ============================================================================
// Log Analytics Workspace
// ============================================================================

module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'log-analytics-deployment'
  scope: rg
  params: {
    name: logAnalyticsName
    location: location
  }
}

// ============================================================================
// Container Apps Environment
// ============================================================================

module containerEnv 'modules/container-env.bicep' = {
  name: 'container-env-deployment'
  scope: rg
  params: {
    name: containerEnvName
    location: location
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
  }
}

// ============================================================================
// Backend Container App
// ============================================================================

module backend 'modules/container-app.bicep' = {
  name: 'backend-deployment'
  scope: rg
  params: {
    name: backendAppName
    location: location
    containerEnvId: containerEnv.outputs.environmentId
    containerImage: '${acr.outputs.loginServer}/${appName}-backend:${imageTag}'
    containerPort: 8500
    isExternal: false
    minReplicas: 1
    maxReplicas: 3
    cpu: '0.5'
    memory: '1Gi'
    env: [
      { name: 'LLM_PROVIDER', value: llmProvider }
      { name: 'AZURE_OPENAI_ENDPOINT', secretRef: 'azure-openai-endpoint' }
      { name: 'AZURE_OPENAI_API_KEY', secretRef: 'azure-openai-key' }
      { name: 'AZURE_OPENAI_DEPLOYMENT', value: azureOpenAIDeployment }
      { name: 'AZURE_OPENAI_API_VERSION', value: '2024-02-15-preview' }
      { name: 'EXCHANGE_DEFAULT_PROVIDER', value: enableBitget ? 'bitget' : 'coingecko' }
      { name: 'BITGET_API_KEY', secretRef: 'bitget-api-key' }
      { name: 'BITGET_API_SECRET', secretRef: 'bitget-api-secret' }
      { name: 'BITGET_PASSPHRASE', secretRef: 'bitget-passphrase' }
      { name: 'PYTHONUNBUFFERED', value: '1' }
    ]
    secrets: [
      { name: 'azure-openai-endpoint', value: azureOpenAIEndpoint }
      { name: 'azure-openai-key', value: azureOpenAIApiKey }
      { name: 'bitget-api-key', value: bitgetApiKey }
      { name: 'bitget-api-secret', value: bitgetApiSecret }
      { name: 'bitget-passphrase', value: bitgetPassphrase }
    ]
    registryServer: acr.outputs.loginServer
    registryUsername: acr.outputs.adminUsername
    registryPassword: acr.outputs.adminPassword
  }
}

// ============================================================================
// Frontend Container App
// ============================================================================

module frontend 'modules/container-app.bicep' = {
  name: 'frontend-deployment'
  scope: rg
  params: {
    name: frontendAppName
    location: location
    containerEnvId: containerEnv.outputs.environmentId
    containerImage: '${acr.outputs.loginServer}/${appName}-frontend:${imageTag}'
    containerPort: 80
    isExternal: true
    minReplicas: 1
    maxReplicas: 5
    cpu: '0.25'
    memory: '0.5Gi'
    env: [
      { name: 'API_URL', value: 'https://${backend.outputs.fqdn}' }
      { name: 'WS_URL', value: 'wss://${backend.outputs.fqdn}' }
    ]
    secrets: []
    registryServer: acr.outputs.loginServer
    registryUsername: acr.outputs.adminUsername
    registryPassword: acr.outputs.adminPassword
  }
}

// ============================================================================
// Outputs
// ============================================================================

output resourceGroupName string = rg.name
output acrLoginServer string = acr.outputs.loginServer
output backendUrl string = 'https://${backend.outputs.fqdn}'
output frontendUrl string = 'https://${frontend.outputs.fqdn}'
