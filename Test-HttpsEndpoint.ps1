# Bypass SSL verification for self-signed certificates
add-type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
    public bool CheckValidationResult(
        ServicePoint srvPoint, X509Certificate certificate,
        WebRequest request, int certificateProblem) {
        return true;
    }
}
"@
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy

# Test the endpoint
$endpoint = az container show --resource-group asksphere-resource-group --name asksphere-backend --query ipAddress.fqdn --output tsv
Write-Output "Raw endpoint output: $endpoint"
if (-not $endpoint) {
    Write-Output "FQDN not retrieved. Trying IP address..."
    $endpoint = az container show --resource-group asksphere-resource-group --name asksphere-backend --query ipAddress.ip --output tsv
    Write-Output "Raw IP output: $endpoint"
    if (-not $endpoint) {
        Write-Output "Failed to retrieve endpoint. Checking container state..."
        az container show --resource-group asksphere-resource-group --name asksphere-backend --query "{state:instanceView.state, ip:ipAddress.ip, fqdn:ipAddress.fqdn}" --output table
        exit
    }
}
Write-Output "Endpoint: $endpoint"
$baseUri = "https://$($endpoint):5000"
Write-Output "Testing URI: $baseUri/"
$response = Invoke-WebRequest -Uri "$baseUri/" -Method Get
Write-Output "StatusCode: $($response.StatusCode)"
Write-Output "Headers: $($response.Headers | ConvertTo-Json)"
Write-Output "Content: $($response.Content)"
Write-Output "Testing URI: $baseUri/communities"
$response = Invoke-WebRequest -Uri "$baseUri/communities" -Method Get
Write-Output "StatusCode: $($response.StatusCode)"
Write-Output "Headers: $($response.Headers | ConvertTo-Json)"
Write-Output "Content: $($response.Content)"
Write-Output "Testing URI: $baseUri/debug"
$response = Invoke-WebRequest -Uri "$baseUri/debug" -Method Get
Write-Output "StatusCode: $($response.StatusCode)"
Write-Output "Headers: $($response.Headers | ConvertTo-Json)"
Write-Output "Content: $($response.Content)"
az container logs --resource-group asksphere-resource-group --name asksphere-backend