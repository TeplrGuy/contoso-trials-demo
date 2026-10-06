@description('Azure AI Search service name.')
param name string

@description('Location for the Azure AI Search service.')
param location string = resourceGroup().location

@description('Azure AI Search SKU.')
param sku string = 'basic'

@description('Semantic search mode. Use free when the SKU supports it; otherwise use disabled.')
param semanticSearch string = 'free'

@description('Tags to apply to the search service.')
param tags object = {}

resource searchService 'Microsoft.Search/searchServices@2025-05-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    publicNetworkAccess: 'enabled'
    semanticSearch: semanticSearch
    disableLocalAuth: false
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

output name string = searchService.name
output endpoint string = 'https://${searchService.name}.search.windows.net'
