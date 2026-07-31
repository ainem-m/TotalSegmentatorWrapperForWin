[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$principal = [Security.Principal.WindowsPrincipal]::new(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)
if (-not $principal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)) {
    throw "Run this installer from an elevated PowerShell window."
}

$distributionRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$packages = @(Get-ChildItem -LiteralPath $distributionRoot -Filter "*.msix" -File)
$certificates = @(Get-ChildItem -LiteralPath $distributionRoot -Filter "*.cer" -File)
if ($packages.Count -ne 1 -or $certificates.Count -ne 1) {
    throw "Exactly one MSIX and one public certificate are required."
}

$package = $packages[0]
$certificatePath = $certificates[0].FullName
$certificate = [Security.Cryptography.X509Certificates.X509Certificate2]::new(
    $certificatePath
)
if ($certificate.Subject -ne "CN=TotalSegmentatorWrapperForWin Alpha") {
    throw "The alpha certificate publisher does not match."
}

$signature = Get-AuthenticodeSignature -FilePath $package.FullName
if ($null -eq $signature.SignerCertificate) {
    throw "The MSIX signer certificate is unavailable."
}
if ($signature.SignerCertificate.Thumbprint -ne $certificate.Thumbprint) {
    throw "The MSIX signature does not match the bundled certificate."
}

Import-Certificate `
    -FilePath $certificatePath `
    -CertStoreLocation "Cert:\LocalMachine\TrustedPeople" | Out-Null

$trustedSignature = Get-AuthenticodeSignature -FilePath $package.FullName
$trustedStatusAccepted = (
    $trustedSignature.Status -eq
    [Management.Automation.SignatureStatus]::Valid
)
if ($trustedSignature.Status -eq
    [Management.Automation.SignatureStatus]::UnknownError) {
    $chain = [Security.Cryptography.X509Certificates.X509Chain]::new()
    $chain.ChainPolicy.RevocationMode =
        [Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
    $chain.Build($trustedSignature.SignerCertificate) | Out-Null
    $chainErrors = @(
        $chain.ChainStatus |
        Where-Object {
            $_.Status -ne
            [Security.Cryptography.X509Certificates.X509ChainStatusFlags]::NoError
        }
    )
    $trustedStatusAccepted = (
        $chainErrors.Count -eq 1 -and
        $chainErrors[0].Status -eq
        [Security.Cryptography.X509Certificates.X509ChainStatusFlags]::UntrustedRoot
    )
    $chain.Dispose()
}
if (-not $trustedStatusAccepted) {
    throw "The MSIX signature is invalid after certificate installation."
}

Add-AppxPackage -Path $package.FullName -ForceApplicationShutdown
$installed = Get-AppxPackage -Name "TotalSegmentatorWrapperForWin.Alpha"
if ($null -eq $installed) {
    throw "The installed MSIX package could not be verified."
}

Write-Host "Installation completed. Launch TotalSegmentator Wrapper for Windows Alpha from Start."
