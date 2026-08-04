[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$WinAppPath,
    [Parameter(Mandatory = $true)]
    [string]$DotNetPath,
    [Parameter(Mandatory = $true)]
    [string]$DotNetPackageSource,
    [Parameter(Mandatory = $true)]
    [string]$PythonRuntimeRoot,
    [Parameter(Mandatory = $true)]
    [string]$TotalSegmentatorHome,
    [Parameter(Mandatory = $true)]
    [string]$DicomNormalizerPath,
    [Parameter(Mandatory = $true)]
    [string]$Dcm2niixPath,
    [Parameter(Mandatory = $true)]
    [string]$CertificateThumbprint,
    [Parameter(Mandatory = $true)]
    [string]$WorkRoot,
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,
    [ValidatePattern("^\d+\.\d+\.\d+\.\d+$")]
    [string]$Version = "0.1.0.0",
    [switch]$KeepStaging
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$packageName = "TotalSegmentatorWrapperForWin.Alpha"
$publisher = "CN=TotalSegmentatorWrapperForWin Alpha"
$displayName = "TotalSegmentator Wrapper for Windows Alpha"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Resolve-RequiredFile([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label was not found."
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

function Resolve-RequiredDirectory([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "$Label was not found."
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

function Invoke-Checked([string]$Label, [scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

function Copy-Tree([string]$Source, [string]$Destination) {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    & robocopy $Source $Destination /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /MT:16 /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -gt 7) {
        throw "Payload copy failed with robocopy exit code $LASTEXITCODE."
    }
}

function Get-ValidatedDicomNormalizer([string]$Path) {
    $doctorOutput = & $Path doctor
    if ($LASTEXITCODE -ne 0) {
        throw "DICOM normalizer doctor failed with exit code $LASTEXITCODE."
    }
    try {
        $doctor = ($doctorOutput | Out-String | ConvertFrom-Json)
    }
    catch {
        throw "DICOM normalizer doctor did not produce valid JSON."
    }
    $mprCapability = if ($null -eq $doctor.capabilities) {
        $null
    }
    else {
        $doctor.capabilities.PSObject.Properties[
            "three_plane_mpr_preview"
        ]
    }
    if (
        $doctor.schema -ne
            "totalsegmentator_wrapper_mac.dicom_normalizer.doctor.v1" -or
        $doctor.status -ne "ok" -or
        $null -eq $mprCapability -or
        $mprCapability.Value -ne $true
    ) {
        throw (
            "DICOM normalizer must report the three_plane_mpr_preview " +
            "capability. Rebuild it from this repository before packaging."
        )
    }
}

$winApp = Resolve-RequiredFile $WinAppPath "winapp CLI"
$dotnet = Resolve-RequiredFile $DotNetPath ".NET SDK"
$dotnetPackages = Resolve-RequiredDirectory `
    $DotNetPackageSource `
    ".NET runtime package source"
$pythonRuntime = Resolve-RequiredDirectory $PythonRuntimeRoot "Python runtime"
$totalSegHome = Resolve-RequiredDirectory $TotalSegmentatorHome "TotalSegmentator model root"
$dicomNormalizer = Resolve-RequiredFile $DicomNormalizerPath "DICOM normalizer"
Get-ValidatedDicomNormalizer $dicomNormalizer | Out-Null
$dcm2niix = Resolve-RequiredFile $Dcm2niixPath "dcm2niix"

$requiredDotNetPackages = [ordered]@{
    "microsoft.aspnetcore.app.runtime.win-x64.10.0.10.nupkg" =
        "1669e0b37959ad5d6306dccc1991ee15863fd08f65dc40fd2addcaffd235d977"
    "microsoft.netcore.app.runtime.win-x64.10.0.10.nupkg" =
        "56899c9057d6981ab9f237d6489e469af043668ab34cfb4199b55f92702b06bb"
    "microsoft.windowsdesktop.app.runtime.win-x64.10.0.10.nupkg" =
        "f57afeb29ba87f687cb5fd6693c82a1161e8b28e79cf380a02087f4c2ba35758"
}
$dotNetPackageEvidence = foreach ($entry in $requiredDotNetPackages.GetEnumerator()) {
    $packagePath = Resolve-RequiredFile `
        (Join-Path $dotnetPackages $entry.Key) `
        ".NET runtime package"
    $actualHash = (
        Get-FileHash -LiteralPath $packagePath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($actualHash -ne $entry.Value) {
        throw "A .NET runtime package hash does not match the pinned closure."
    }
    [pscustomobject]@{
        file = $entry.Key
        sha256 = $actualHash
    }
}

Resolve-RequiredFile `
    (Join-Path $pythonRuntime "Scripts\totalsegmentator-wrapper-coordinator.exe") `
    "production coordinator" | Out-Null
Resolve-RequiredFile (Join-Path $totalSegHome "config.json") "TotalSegmentator config" | Out-Null
foreach ($dataset in @(
    "Dataset115_mandible",
    "Dataset297_TotalSegmentator_total_3mm_1559subj"
)) {
    $datasetRoot = Join-Path $totalSegHome "nnunet\results\$dataset"
    Resolve-RequiredDirectory $datasetRoot $dataset | Out-Null
    $checkpoint = Get-ChildItem `
        -LiteralPath $datasetRoot `
        -Filter "checkpoint_final.pth" `
        -File `
        -Recurse |
        Where-Object Length -gt 0 |
        Select-Object -First 1
    if ($null -eq $checkpoint) {
        throw "A non-empty checkpoint was not found for $dataset."
    }
}

$totalSegConfig = Get-Content `
    -LiteralPath (Join-Path $totalSegHome "config.json") `
    -Raw |
    ConvertFrom-Json
if ($totalSegConfig.send_usage_stats -ne $false) {
    throw "TotalSegmentator usage statistics are not disabled."
}

$thumbprint = ($CertificateThumbprint -replace "\s", "").ToUpperInvariant()
$certificate = Get-Item "Cert:\CurrentUser\My\$thumbprint" -ErrorAction Stop
if ($certificate.Subject -ne $publisher -or -not $certificate.HasPrivateKey) {
    throw "The signing certificate subject or private key is invalid."
}

$absoluteWorkRoot = [IO.Path]::GetFullPath($WorkRoot)
$absoluteOutput = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $absoluteWorkRoot -Force | Out-Null
New-Item -ItemType Directory -Path $absoluteOutput -Force | Out-Null
$buildId = [Guid]::NewGuid().ToString("N")
$stagingRoot = Join-Path $absoluteWorkRoot "build-$buildId"
$packageRoot = Join-Path $stagingRoot "package"
$shellPublish = Join-Path $stagingRoot "shell-publish"
$supervisorPublish = Join-Path $stagingRoot "supervisor-publish"
$wheelSource = Join-Path $stagingRoot "wrapper-source"
$wheelOutput = Join-Path $stagingRoot "wheel"
$manifestRoot = Join-Path $stagingRoot "manifest"
$tempRoot = Join-Path $stagingRoot "temp"
foreach ($directory in @(
    $packageRoot,
    $shellPublish,
    $supervisorPublish,
    $wheelSource,
    $wheelOutput,
    $manifestRoot,
    $tempRoot
)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}

$oldTemp = $env:TEMP
$oldTmp = $env:TMP
$oldTelemetry = $env:WINAPP_CLI_TELEMETRY_OPTOUT
$oldDotnetTelemetry = $env:DOTNET_CLI_TELEMETRY_OPTOUT
$oldDotnetNoLogo = $env:DOTNET_NOLOGO
$oldDotnetHome = $env:DOTNET_CLI_HOME
$oldPipCache = $env:PIP_CACHE_DIR
$env:TEMP = $tempRoot
$env:TMP = $tempRoot
$env:WINAPP_CLI_TELEMETRY_OPTOUT = "1"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
$env:DOTNET_NOLOGO = "1"
$env:DOTNET_CLI_HOME = Join-Path $stagingRoot "dotnet-home"
$env:PIP_CACHE_DIR = Join-Path $stagingRoot "pip-cache"

try {
    $offlineNugetConfig = Join-Path $stagingRoot "NuGet.Config"
    $escapedDotNetPackages = [Security.SecurityElement]::Escape(
        $dotnetPackages
    )
    Set-Content `
        -LiteralPath $offlineNugetConfig `
        -Encoding ascii `
        -Value @(
            '<?xml version="1.0" encoding="utf-8"?>',
            '<configuration>',
            '  <packageSources>',
            '    <clear />',
            ('    <add key="alpha-runtime-packs" value="{0}" />' -f
                $escapedDotNetPackages),
            '  </packageSources>',
            '</configuration>'
        )
    foreach ($project in @(
        (Join-Path `
            $repoRoot `
            "native\windows\CoordinatorShell\CoordinatorShell.csproj"),
        (Join-Path `
            $repoRoot `
            "native\windows\ProcessSupervisor\ProcessSupervisor.csproj")
    )) {
        Invoke-Checked "offline .NET restore" {
            & $dotnet restore `
                $project `
                --runtime win-x64 `
                --configfile $offlineNugetConfig `
                -p:NuGetAudit=false
        }
    }
    Invoke-Checked "WPF self-contained publish" {
        & $dotnet publish `
            (Join-Path $repoRoot "native\windows\CoordinatorShell\CoordinatorShell.csproj") `
            -c Release `
            -r win-x64 `
            --no-restore `
            --self-contained true `
            -p:PublishSingleFile=false `
            -p:UseSharedCompilation=false `
            -o $shellPublish
    }
    Invoke-Checked "Job Object supervisor self-contained publish" {
        & $dotnet publish `
            (Join-Path $repoRoot "native\windows\ProcessSupervisor\ProcessSupervisor.csproj") `
            -c Release `
            -r win-x64 `
            --no-restore `
            --self-contained true `
            -p:PublishSingleFile=true `
            -p:IncludeNativeLibrariesForSelfExtract=true `
            -p:UseSharedCompilation=false `
            -o $supervisorPublish
    }
    Copy-Tree $shellPublish $packageRoot
    Copy-Item `
        (Join-Path $supervisorPublish "tswm-process-supervisor.exe") `
        $packageRoot

    Copy-Tree $pythonRuntime (Join-Path $packageRoot "runtime\python")
    Copy-Tree $totalSegHome (Join-Path $packageRoot "models\totalseg-home")
    Copy-Tree `
        (Join-Path $repoRoot "resources\sample1") `
        (Join-Path $packageRoot "sample1")

    $nativeRoot = Join-Path $packageRoot "runtime\native"
    New-Item -ItemType Directory -Path $nativeRoot -Force | Out-Null
    Copy-Item $dicomNormalizer `
        (Join-Path $nativeRoot "totalsegmentator-wrapper-dicom-normalizer.exe")
    Copy-Item $dcm2niix (Join-Path $nativeRoot "dcm2niix.exe")

    $pythonSitePackages = Join-Path `
        $packageRoot `
        "runtime\python\Lib\site-packages"
    $futureTestFixtures = Join-Path `
        $pythonSitePackages `
        "future\backports\test"
    if (Test-Path -LiteralPath $futureTestFixtures) {
        Remove-Item -LiteralPath $futureTestFixtures -Recurse -Force
    }
    $privateKeyLikeFiles = @(
        Get-ChildItem $packageRoot -File -Recurse |
        Where-Object {
            $_.Extension -in @(".pfx", ".key") -or
            $_.Name -match "(?i)key.*\.pem$"
        }
    )
    if ($privateKeyLikeFiles.Count -ne 0) {
        throw "A private-key-like file remains in the package payload."
    }

    Copy-Item (Join-Path $repoRoot "pyproject.toml") $wheelSource
    foreach ($name in @(
        "README.md",
        "LICENSE",
        "NOTICE",
        "THIRD_PARTY_NOTICES.md"
    )) {
        Copy-Item (Join-Path $repoRoot $name) $wheelSource
    }
    Copy-Tree (Join-Path $repoRoot "src") (Join-Path $wheelSource "src")
    $stagedPython = Join-Path $packageRoot "runtime\python\python.exe"
    Invoke-Checked "wrapper wheel build" {
        & $stagedPython -m pip wheel `
            $wheelSource `
            --no-deps `
            --no-build-isolation `
            --no-index `
            --wheel-dir $wheelOutput
    }
    $wrapperWheels = @(Get-ChildItem $wheelOutput -Filter "*.whl" -File)
    if ($wrapperWheels.Count -ne 1) {
        throw "Exactly one first-party wrapper wheel is required."
    }
    Invoke-Checked "wrapper offline install" {
        & $stagedPython -m pip install `
            --no-index `
            --no-deps `
            --force-reinstall `
            --no-warn-script-location `
            $wrapperWheels[0].FullName
    }
    $sitePackages = $pythonSitePackages
    $legacyMetadata = @(
        Get-ChildItem `
            -LiteralPath $sitePackages `
            -Directory `
            -Filter "totalsegmentator_wrapper_mac-*.dist-info"
    )
    foreach ($metadataDirectory in $legacyMetadata) {
        if ($metadataDirectory.Parent.FullName -ne $sitePackages) {
            throw "Legacy wrapper metadata is outside site-packages."
        }
        Remove-Item -LiteralPath $metadataDirectory.FullName -Recurse -Force
    }
    if (Get-ChildItem `
        -LiteralPath $sitePackages `
        -Directory `
        -Filter "totalsegmentator_wrapper_mac-*.dist-info"
    ) {
        throw "Legacy wrapper distribution metadata remains."
    }

    $legalRoot = Join-Path $packageRoot "legal"
    New-Item -ItemType Directory -Path $legalRoot -Force | Out-Null
    foreach ($name in @(
        "LICENSE",
        "NOTICE",
        "THIRD_PARTY_NOTICES.md"
    )) {
        Copy-Item (Join-Path $repoRoot $name) $legalRoot
    }
    Copy-Tree `
        (Join-Path $repoRoot "resources\third_party") `
        (Join-Path $legalRoot "third_party")
    Invoke-Checked "runtime license inventory" {
        & $stagedPython `
            (Join-Path $repoRoot "scripts\write_runtime_license_inventory.py") `
            --output (Join-Path $legalRoot "runtime-license-inventory.json")
    }

    Copy-Item (Join-Path $packageRoot "tswm-windows-shell.exe") $manifestRoot
    Push-Location $manifestRoot
    try {
        Invoke-Checked "MSIX manifest generation" {
            & $winApp manifest generate . `
                --package-name $packageName `
                --publisher-name $publisher `
                --version $Version `
                --description "Non-clinical alpha preview for research, education, and verification only." `
                --executable "tswm-windows-shell.exe"
        }
    }
    finally {
        Pop-Location
    }
    Remove-Item -LiteralPath (Join-Path $manifestRoot "tswm-windows-shell.exe") -Force
    Copy-Tree (Join-Path $manifestRoot "Assets") (Join-Path $packageRoot "Assets")

    [xml]$manifest = Get-Content `
        -LiteralPath (Join-Path $manifestRoot "Package.appxmanifest") `
        -Raw
    $namespace = New-Object Xml.XmlNamespaceManager($manifest.NameTable)
    $namespace.AddNamespace(
        "f",
        "http://schemas.microsoft.com/appx/manifest/foundation/windows10"
    )
    $namespace.AddNamespace(
        "uap",
        "http://schemas.microsoft.com/appx/manifest/uap/windows10"
    )
    $manifest.SelectSingleNode("//f:Properties/f:DisplayName", $namespace).InnerText =
        $displayName
    $manifest.SelectSingleNode(
        "//f:Properties/f:PublisherDisplayName",
        $namespace
    ).InnerText = "TotalSegmentatorWrapperForWin Alpha"
    $visual = $manifest.SelectSingleNode("//uap:VisualElements", $namespace)
    $visual.SetAttribute("DisplayName", $displayName)
    $manifest.Save((Join-Path $manifestRoot "Package.appxmanifest"))

    $unsignedPackage = Join-Path `
        $stagingRoot `
        ("{0}_{1}_x64_unsigned.msix" -f $packageName, $Version)
    Invoke-Checked "MSIX package creation" {
        & $winApp package `
            $packageRoot `
            --manifest (Join-Path $manifestRoot "Package.appxmanifest") `
            --output $unsignedPackage `
            --exe "tswm-windows-shell.exe" `
            --skip-pri
    }

    $packageFileName = "{0}_{1}_x64.msix" -f $packageName, $Version
    $signedPackage = Join-Path $absoluteOutput $packageFileName
    Copy-Item $unsignedPackage $signedPackage -Force
    Invoke-Checked "MSIX signing" {
        & $winApp tool signtool -- `
            sign `
            /fd SHA256 `
            /sha1 $thumbprint `
            /s My `
            $signedPackage
    }
    $signature = Get-AuthenticodeSignature -FilePath $signedPackage
    $signerMatches = (
        $null -ne $signature.SignerCertificate -and
        $signature.SignerCertificate.Thumbprint -eq $thumbprint -and
        $signature.SignerCertificate.Subject -eq $publisher -and
        $signature.SignerCertificate.Issuer -eq $publisher
    )
    $signatureTrustAccepted = (
        $signature.Status -eq
        [Management.Automation.SignatureStatus]::Valid
    )
    if ($signature.Status -eq
        [Management.Automation.SignatureStatus]::UnknownError) {
        $chain = [Security.Cryptography.X509Certificates.X509Chain]::new()
        $chain.ChainPolicy.RevocationMode =
            [Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
        $chain.Build($signature.SignerCertificate) | Out-Null
        $chainErrors = @(
            $chain.ChainStatus |
            Where-Object {
                $_.Status -ne
                [Security.Cryptography.X509Certificates.X509ChainStatusFlags]::NoError
            }
        )
        $signatureTrustAccepted = (
            $chainErrors.Count -eq 1 -and
            $chainErrors[0].Status -eq
            [Security.Cryptography.X509Certificates.X509ChainStatusFlags]::UntrustedRoot
        )
        $chain.Dispose()
    }
    if (-not $signerMatches -or -not $signatureTrustAccepted) {
        throw "The signed MSIX did not pass trusted signer verification."
    }

    $publicCertificate = Join-Path $absoluteOutput "TotalSegmentatorWrapperForWin-Alpha.cer"
    Export-Certificate `
        -Cert $certificate `
        -FilePath $publicCertificate `
        -Force | Out-Null
    foreach ($name in @(
        "install_alpha_msix.ps1",
        "uninstall_alpha_msix.ps1"
    )) {
        Copy-Item (Join-Path $repoRoot "scripts\$name") $absoluteOutput -Force
    }
    Copy-Item `
        (Join-Path $repoRoot "docs\ALPHA_INSTALL_JA.md") `
        (Join-Path $absoluteOutput "README_ALPHA_JA.md") `
        -Force

    $hashTargets = @(
        $signedPackage,
        $publicCertificate,
        (Join-Path $absoluteOutput "install_alpha_msix.ps1"),
        (Join-Path $absoluteOutput "uninstall_alpha_msix.ps1"),
        (Join-Path $absoluteOutput "README_ALPHA_JA.md")
    )
    $hashLines = foreach ($target in $hashTargets) {
        $hash = Get-FileHash -LiteralPath $target -Algorithm SHA256
        "{0}  {1}" -f $hash.Hash.ToLowerInvariant(), (Split-Path -Leaf $target)
    }
    Set-Content `
        -LiteralPath (Join-Path $absoluteOutput "SHA256SUMS.txt") `
        -Value $hashLines `
        -Encoding ascii

    $packageHash = Get-FileHash $signedPackage -Algorithm SHA256
    [pscustomobject]@{
        schema = "totalsegmentator_wrapper.windows_alpha_msix_build.v1"
        status = "pass"
        package_name = $packageName
        package_version = $Version
        architecture = "x64"
        package_file = $packageFileName
        package_bytes = (Get-Item $signedPackage).Length
        package_sha256 = $packageHash.Hash.ToLowerInvariant()
        publisher = $publisher
        certificate_thumbprint = $thumbprint
        certificate_not_after = $certificate.NotAfter.ToUniversalTime().ToString("O")
        private_key_distributed = $false
        python_runtime_network_resolution = $false
        dotnet_runtime_package_network_resolution = $false
        dotnet_runtime_packages = @($dotNetPackageEvidence)
        bundled_totalsegmentator_datasets = @(
            "Dataset115_mandible",
            "Dataset297_TotalSegmentator_total_3mm_1559subj"
        )
        bundled_additional_models = @()
        windows_10_install = "pending"
        windows_11_install = "unverified"
    } |
        ConvertTo-Json -Depth 5 |
        Set-Content `
            -LiteralPath (Join-Path $absoluteOutput "build-manifest.json") `
            -Encoding utf8

    Write-Output $signedPackage
}
finally {
    $env:TEMP = $oldTemp
    $env:TMP = $oldTmp
    $env:WINAPP_CLI_TELEMETRY_OPTOUT = $oldTelemetry
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = $oldDotnetTelemetry
    $env:DOTNET_NOLOGO = $oldDotnetNoLogo
    $env:DOTNET_CLI_HOME = $oldDotnetHome
    $env:PIP_CACHE_DIR = $oldPipCache
    if (-not $KeepStaging -and (Test-Path -LiteralPath $stagingRoot)) {
        $resolvedStaging = (Resolve-Path -LiteralPath $stagingRoot).Path
        $resolvedWork = (Resolve-Path -LiteralPath $absoluteWorkRoot).Path
        if (-not $resolvedStaging.StartsWith(
            $resolvedWork + [IO.Path]::DirectorySeparatorChar
        )) {
            throw "The staging cleanup target is outside the work root."
        }
        Remove-Item -LiteralPath $resolvedStaging -Recurse -Force
    }
}
