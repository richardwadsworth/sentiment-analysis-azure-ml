// Parameters
param location string
param storageAccountName string
param keyVaultName string
param amlWorkspaceName string
param computeName string

// Storage Account with security best practices
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    encryption: {
      services: {
        blob: {
          enabled: true
        }
        file: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
  tags: {
    purpose: 'ml-data-storage'
    environment: 'dev'
  }
}

// Key Vault for secure credential storage with RBAC enabled
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enabledForDeployment: false
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: false
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
  tags: {
    purpose: 'ml-secrets'
    environment: 'dev'
  }
}

// Log Analytics Workspace (required for Application Insights)
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${uniqueString(resourceGroup().id)}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
  tags: {
    purpose: 'ml-logging'
    environment: 'dev'
  }
}

// Application Insights for monitoring
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'ai-${uniqueString(resourceGroup().id)}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
  tags: {
    purpose: 'ml-monitoring'
    environment: 'dev'
  }
}

// Azure ML Workspace with system-assigned managed identity and identity-based access
resource amlWorkspace 'Microsoft.MachineLearningServices/workspaces@2023-06-01-preview' = {
  name: amlWorkspaceName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    storageAccount: storage.id
    keyVault: keyVault.id
    applicationInsights: appInsights.id
    publicNetworkAccess: 'Enabled'
    hbiWorkspace: false
    v1LegacyMode: false
    // Configure identity-based access to storage
    systemDatastoresAuthMode: 'identity'
  }
  tags: {
    purpose: 'ml-workspace'
    environment: 'dev'
  }
}

// Compute Cluster with auto-scaling, cost optimisation, and system-assigned managed identity
resource compute 'Microsoft.MachineLearningServices/workspaces/computes@2023-04-01' = {
  parent: amlWorkspace
  name: computeName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    computeType: 'AmlCompute'
    properties: {
      vmSize: 'STANDARD_DS3_V2'
      vmPriority: 'Dedicated'
      scaleSettings: {
        minNodeCount: 0
        maxNodeCount: 2
        nodeIdleTimeBeforeScaleDown: 'PT120S'
      }
      osType: 'Linux'
      enableNodePublicIp: true
      isolatedNetwork: false
    }
  }
}

// RBAC Role Assignments
// Azure ML's automatic role assignment is unreliable for compute clusters, so we explicitly assign required roles

// Storage Blob Data Contributor role for Compute Cluster managed identity
resource computeStorageBlobContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, compute.id, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: compute.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Storage Table Data Contributor role for Compute Cluster managed identity (for Table Storage)
resource computeStorageTableContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, compute.id, '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3') // Storage Table Data Contributor
    principalId: compute.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Storage Account Contributor role for Compute Cluster managed identity (needed to create tables)
resource computeStorageAccountContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, compute.id, '17d1049b-9a84-46fb-8f53-869881c3d3ab')
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '17d1049b-9a84-46fb-8f53-869881c3d3ab') // Storage Account Contributor
    principalId: compute.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Key Vault Secrets User role for Compute Cluster managed identity
resource computeKeyVaultSecretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, compute.id, '4633458b-17de-408a-b874-0445c86b69e6')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: compute.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output storageAccountName string = storage.name
output storageAccountId string = storage.id
output keyVaultName string = keyVault.name
output keyVaultId string = keyVault.id
output appInsightsName string = appInsights.name
output appInsightsId string = appInsights.id
output logAnalyticsName string = logAnalytics.name
output logAnalyticsId string = logAnalytics.id
output amlWorkspaceName string = amlWorkspace.name
output amlWorkspaceId string = amlWorkspace.id
output amlPrincipalId string = amlWorkspace.identity.principalId
output computeName string = compute.name
output computeId string = compute.id
output computePrincipalId string = compute.identity.principalId
