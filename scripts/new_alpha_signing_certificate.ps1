[CmdletBinding()]
param(
    [string]$Publisher = "CN=TotalSegmentatorWrapperForWin Alpha",
    [string]$FriendlyName = "TotalSegmentatorWrapperForWin Alpha MSIX",
    [ValidateRange(30, 825)]
    [int]$ValidDays = 365,
    [Parameter(Mandatory = $true)]
    [string]$PublicCertificatePath,
    [switch]$TrustForLocalMachine
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$certificate = New-SelfSignedCertificate `
    -Type Custom `
    -Subject $Publisher `
    -FriendlyName $FriendlyName `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -KeyAlgorithm RSA `
    -KeyLength 3072 `
    -HashAlgorithm SHA256 `
    -KeyUsage DigitalSignature `
    -KeySpec Signature `
    -TextExtension @(
        "2.5.29.37={text}1.3.6.1.5.5.7.3.3",
        "2.5.29.19={text}"
    ) `
    -NotAfter (Get-Date).AddDays($ValidDays)

$publicPath = [IO.Path]::GetFullPath($PublicCertificatePath)
$publicParent = Split-Path -Parent $publicPath
New-Item -ItemType Directory -Path $publicParent -Force | Out-Null
Export-Certificate -Cert $certificate -FilePath $publicPath -Force | Out-Null

if ($TrustForLocalMachine) {
    $principal = [Security.Principal.WindowsPrincipal]::new(
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
    if (-not $principal.IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )) {
        throw "Local-machine trust requires an elevated PowerShell window."
    }
    Import-Certificate `
        -FilePath $publicPath `
        -CertStoreLocation "Cert:\LocalMachine\TrustedPeople" | Out-Null
}

[pscustomobject]@{
    schema = "totalsegmentator_wrapper.windows_alpha_signing_certificate.v1"
    subject = $certificate.Subject
    thumbprint = $certificate.Thumbprint
    not_before = $certificate.NotBefore.ToUniversalTime().ToString("O")
    not_after = $certificate.NotAfter.ToUniversalTime().ToString("O")
    private_key_exported = $false
    trusted_for_local_machine = [bool]$TrustForLocalMachine
} | ConvertTo-Json
