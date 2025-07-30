param location string = 'westus'
param resourceGroup string = 'asksphere-resource-group'
param gatewayName string = 'asksphere-gateway'
param vnetName string = 'asksphere-vnet'
param subnetName string = 'appgw-subnet'
param publicIpName string = 'asksphere-public-ip'
param backendIp string = '23.99.93.73' // From az container show output

resource publicIp 'Microsoft.Network/publicIPAddresses@2023-11-01' = {
  name: publicIpName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    subnets: [
      {
        name: subnetName
        properties: {
          addressPrefix: '10.0.1.0/24'
        }
      }
    ]
  }
}

resource appGateway 'Microsoft.Network/applicationGateways@2023-11-01' = {
  name: gatewayName
  location: location
  properties: {
    sku: {
      name: 'Standard_v2'
      tier: 'Standard_v2'
      capacity: 2
    }
    gatewayIPConfigurations: [
      {
        name: 'appGatewayIpConfig'
        properties: {
          subnet: {
            id: vnet.properties.subnets[0].id
          }
        }
      }
    ]
    frontendIPConfigurations: [
      {
        name: 'appGatewayFrontendIP'
        properties: {
          publicIPAddress: {
            id: publicIp.id
          }
        }
      }
    ]
    frontendPorts: [
      {
        name: 'port-443'
        properties: {
          port: 443
        }
      }
    ]
    backendAddressPools: [
      {
        name: 'asksphere-backend-pool'
        properties: {
          backendAddresses: [
            {
              ipAddress: backendIp
            }
          ]
        }
      }
    ]
    backendHttpSettingsCollection: [
      {
        name: 'asksphere-http-settings'
        properties: {
          port: 5000
          protocol: 'Http'
          cookieBasedAffinity: 'Disabled'
          requestTimeout: 30
        }
      }
    ]
    httpListeners: [
      {
        name: 'asksphere-listener'
        properties: {
          frontendIPConfiguration: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendIPConfigurations', gatewayName, 'appGatewayFrontendIP')
          }
          frontendPort: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendPorts', gatewayName, 'port-443')
          }
          protocol: 'Https'
          sslCertificate: {
            id: resourceId('Microsoft.Network/applicationGateways/sslCertificates', gatewayName, 'asksphere-cert')
          }
        }
      }
    ]
    sslCertificates: [
      {
        name: 'asksphere-cert'
        properties: {
          data: '<base64-encoded-cert>' // Replace with base64-encoded .pfx or .cer
          password: '' // Leave empty for .cer or set for .pfx
        }
      }
    ]
    requestRoutingRules: [
      {
        name: 'asksphere-rule'
        properties: {
          ruleType: 'Basic'
          priority: 100
          httpListener: {
            id: resourceId('Microsoft.Network/applicationGateways/httpListeners', gatewayName, 'asksphere-listener')
          }
          backendAddressPool: {
            id: resourceId('Microsoft.Network/applicationGateways/backendAddressPools', gatewayName, 'asksphere-backend-pool')
          }
          backendHttpSettings: {
            id: resourceId('Microsoft.Network/applicationGateways/backendHttpSettingsCollection', gatewayName, 'asksphere-http-settings')
          }
        }
      }
    ]
  }
}

output gatewayIp string = publicIp.properties.ipAddress