[CmdletBinding()]
param(
    [switch]$RemoveTrustedCertificate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($RemoveTrustedCertificate) {
    $principal = [Security.Principal.WindowsPrincipal]::new(
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
    if (-not $principal.IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )) {
        throw "Certificate removal requires an elevated PowerShell window."
    }
}

$packages = @(Get-AppxPackage -Name "TotalSegmentatorWrapperForWin.Alpha")
foreach ($package in $packages) {
    Remove-AppxPackage -Package $package.PackageFullName
}

if ($RemoveTrustedCertificate) {
    $distributionRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $certificates = @(
        Get-ChildItem `
            -LiteralPath $distributionRoot `
            -Filter "*.cer" `
            -File
    )
    if ($certificates.Count -ne 1) {
        throw "Exactly one public certificate is required for removal."
    }
    $certificate =
        [Security.Cryptography.X509Certificates.X509Certificate2]::new(
            $certificates[0].FullName
        )
    foreach ($storePath in @(
        "Cert:\LocalMachine\TrustedPeople",
        "Cert:\CurrentUser\Root",
        "Cert:\CurrentUser\TrustedPeople"
    )) {
        Get-ChildItem $storePath |
            Where-Object Thumbprint -eq $certificate.Thumbprint |
            Remove-Item
    }
}

Write-Host "Uninstall completed. Existing result files were not removed."
