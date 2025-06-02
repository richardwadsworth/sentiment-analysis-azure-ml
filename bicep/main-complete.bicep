targetScope = 'subscription'

// Parameters - no default values, must be provided by caller
param resourceGroupName string
param location string
param storageAccountName string
param keyVaultName string
param amlWorkspaceName string
param computeName string

// Create Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: {
    project: 'sentiment-analysis'
    environment: 'dev'
    costCentre: 'ml-ops'
  }
}

// Deploy all resources in one go
module completeInfrastructure 'modules/complete-infrastructure.bicep' = {
  name: 'sentiment-analysis-complete'
  scope: rg
  params: {
    location: location
    storageAccountName: storageAccountName
    keyVaultName: keyVaultName
    amlWorkspaceName: amlWorkspaceName
    computeName: computeName
  }
}

// Outputs
output resourceGroupName string = rg.name
output storageAccountName string = completeInfrastructure.outputs.storageAccountName
output keyVaultName string = completeInfrastructure.outputs.keyVaultName
output appInsightsName string = completeInfrastructure.outputs.appInsightsName
output logAnalyticsName string = completeInfrastructure.outputs.logAnalyticsName
output amlWorkspaceName string = completeInfrastructure.outputs.amlWorkspaceName
output computeName string = completeInfrastructure.outputs.computeName
output amlPrincipalId string = completeInfrastructure.outputs.amlPrincipalId
output computePrincipalId string = completeInfrastructure.outputs.computePrincipalId
output location string = location

output instructions string = '''
Deployment Complete!
Your Azure ML infrastructure is now ready:
- ML Workspace: ${completeInfrastructure.outputs.amlWorkspaceName} (with system-assigned managed identity)
- Compute Cluster: ${completeInfrastructure.outputs.computeName} (auto-scales 0-2 nodes, with system-assigned managed identity)
- Storage Account: ${completeInfrastructure.outputs.storageAccountName} (with explicit RBAC permissions)
- Key Vault: ${completeInfrastructure.outputs.keyVaultName} (with explicit RBAC permissions)

RBAC Configuration (Explicitly Assigned):
- Compute Cluster managed identity has Storage Blob Data Contributor role on storage account
- Compute Cluster managed identity has Key Vault Secrets User role on key vault
- ML Workspace managed identity gets automatic permissions from Azure ML
- All AuthorizationPermissionMismatch issues should be resolved

Next Steps:
1. Navigate to Azure ML Studio: https://ml.azure.com
2. Select your workspace: ${completeInfrastructure.outputs.amlWorkspaceName}
3. Upload your training data to the default datastore
4. Create and run your sentiment analysis pipeline

Note: The explicit RBAC assignments ensure compute clusters can access storage and key vault resources.
'''
