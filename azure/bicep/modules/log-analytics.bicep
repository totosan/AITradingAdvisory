// Log Analytics Workspace Module

@description('Name of the Log Analytics workspace')
param name string

@description('Location for the workspace')
param location string

@description('Retention period in days')
param retentionInDays int = 30

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: name
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

output workspaceId string = logAnalytics.id
output workspaceKey string = logAnalytics.listKeys().primarySharedKey
output customerId string = logAnalytics.properties.customerId
