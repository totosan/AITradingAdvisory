// Container Apps Environment Module

@description('Name of the Container Apps Environment')
param name string

@description('Location for the environment')
param location string

@description('Log Analytics Workspace ID')
param logAnalyticsWorkspaceId string

resource containerEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: name
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
    zoneRedundant: false
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

output environmentId string = containerEnv.id
output defaultDomain string = containerEnv.properties.defaultDomain
