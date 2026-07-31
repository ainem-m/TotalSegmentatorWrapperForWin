[CmdletBinding()]
param(
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
    [string]$WorkRoot,
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,
    [ValidatePattern("^\d+\.\d+\.\d+\.\d+$")]
    [string]$Version = "0.1.0.0",
    [switch]$KeepStaging
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$portableDirectoryName = "TotalSegmentatorWrapperForWin-Alpha-Portable"
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
    & robocopy `
        $Source `
        $Destination `
        /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /MT:16 `
        /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -gt 7) {
        throw "Payload copy failed with robocopy exit code $LASTEXITCODE."
    }
}

$dotnet = Resolve-RequiredFile $DotNetPath ".NET SDK"
$dotnetPackages = Resolve-RequiredDirectory `
    $DotNetPackageSource `
    ".NET runtime package source"
$pythonRuntime = Resolve-RequiredDirectory $PythonRuntimeRoot "Python runtime"
$totalSegHome = Resolve-RequiredDirectory `
    $TotalSegmentatorHome `
    "TotalSegmentator model root"
$dicomNormalizer = Resolve-RequiredFile `
    $DicomNormalizerPath `
    "DICOM normalizer"
$dcm2niix = Resolve-RequiredFile $Dcm2niixPath "dcm2niix"

$requiredDotNetPackages = [ordered]@{
    "microsoft.aspnetcore.app.runtime.win-x64.10.0.10.nupkg" =
        "1669e0b37959ad5d6306dccc1991ee15863fd08f65dc40fd2addcaffd235d977"
    "microsoft.netcore.app.runtime.win-x64.10.0.10.nupkg" =
        "56899c9057d6981ab9f237d6489e469af043668ab34cfb4199b55f92702b06bb"
    "microsoft.windowsdesktop.app.runtime.win-x64.10.0.10.nupkg" =
        "f57afeb29ba87f687cb5fd6693c82a1161e8b28e79cf380a02087f4c2ba35758"
}
$dotNetPackageEvidence = foreach (
    $entry in $requiredDotNetPackages.GetEnumerator()
) {
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
    (Join-Path $pythonRuntime "python.exe") `
    "app-private Python" | Out-Null
Resolve-RequiredFile `
    (Join-Path $totalSegHome "config.json") `
    "TotalSegmentator config" | Out-Null
$requiredDatasets = @(
    "Dataset115_mandible",
    "Dataset297_TotalSegmentator_total_3mm_1559subj"
)
foreach ($dataset in $requiredDatasets) {
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

$absoluteWorkRoot = [IO.Path]::GetFullPath($WorkRoot)
$absoluteOutput = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $absoluteWorkRoot -Force | Out-Null
New-Item -ItemType Directory -Path $absoluteOutput -Force | Out-Null
$buildId = [Guid]::NewGuid().ToString("N")
$stagingRoot = Join-Path $absoluteWorkRoot "build-$buildId"
$portableRoot = Join-Path $stagingRoot $portableDirectoryName
$shellPublish = Join-Path $stagingRoot "shell-publish"
$supervisorPublish = Join-Path $stagingRoot "supervisor-publish"
$wheelSource = Join-Path $stagingRoot "wrapper-source"
$wheelOutput = Join-Path $stagingRoot "wheel"
$evidenceRoot = Join-Path $stagingRoot "evidence"
$tempRoot = Join-Path $stagingRoot "temp"
foreach ($directory in @(
    $portableRoot,
    $shellPublish,
    $supervisorPublish,
    $wheelSource,
    $wheelOutput,
    $evidenceRoot,
    $tempRoot
)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}

$oldTemp = $env:TEMP
$oldTmp = $env:TMP
$oldDotnetTelemetry = $env:DOTNET_CLI_TELEMETRY_OPTOUT
$oldDotnetNoLogo = $env:DOTNET_NOLOGO
$oldDotnetHome = $env:DOTNET_CLI_HOME
$oldPipCache = $env:PIP_CACHE_DIR
$oldPythonBytecode = $env:PYTHONDONTWRITEBYTECODE
$env:TEMP = $tempRoot
$env:TMP = $tempRoot
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
$env:DOTNET_NOLOGO = "1"
$env:DOTNET_CLI_HOME = Join-Path $stagingRoot "dotnet-home"
$env:PIP_CACHE_DIR = Join-Path $stagingRoot "pip-cache"
$env:PYTHONDONTWRITEBYTECODE = "1"

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
            (Join-Path `
                $repoRoot `
                "native\windows\CoordinatorShell\CoordinatorShell.csproj") `
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
            (Join-Path `
                $repoRoot `
                "native\windows\ProcessSupervisor\ProcessSupervisor.csproj") `
            -c Release `
            -r win-x64 `
            --no-restore `
            --self-contained true `
            -p:PublishSingleFile=true `
            -p:IncludeNativeLibrariesForSelfExtract=true `
            -p:UseSharedCompilation=false `
            -o $supervisorPublish
    }
    Copy-Tree $shellPublish $portableRoot
    Copy-Item `
        (Join-Path $supervisorPublish "tswm-process-supervisor.exe") `
        $portableRoot

    Copy-Tree $pythonRuntime (Join-Path $portableRoot "runtime\python")
    Copy-Tree $totalSegHome (Join-Path $portableRoot "models\totalseg-home")
    Copy-Tree `
        (Join-Path $repoRoot "resources\sample1") `
        (Join-Path $portableRoot "sample1")

    $nativeRoot = Join-Path $portableRoot "runtime\native"
    New-Item -ItemType Directory -Path $nativeRoot -Force | Out-Null
    Copy-Item $dicomNormalizer `
        (Join-Path $nativeRoot "totalsegmentator-wrapper-dicom-normalizer.exe")
    Copy-Item $dcm2niix (Join-Path $nativeRoot "dcm2niix.exe")

    $pythonSitePackages = Join-Path `
        $portableRoot `
        "runtime\python\Lib\site-packages"
    $futureTestFixtures = Join-Path `
        $pythonSitePackages `
        "future\backports\test"
    if (Test-Path -LiteralPath $futureTestFixtures) {
        Remove-Item -LiteralPath $futureTestFixtures -Recurse -Force
    }
    $privateKeyLikeFiles = @(
        Get-ChildItem $portableRoot -File -Recurse |
        Where-Object {
            $_.Extension -in @(".pfx", ".key") -or
            $_.Name -match "(?i)key.*\.pem$"
        }
    )
    if ($privateKeyLikeFiles.Count -ne 0) {
        throw "A private-key-like file remains in the portable payload."
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
    $stagedPython = Join-Path $portableRoot "runtime\python\python.exe"
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
    $legacyMetadata = @(
        Get-ChildItem `
            -LiteralPath $pythonSitePackages `
            -Directory `
            -Filter "totalsegmentator_wrapper_mac-*.dist-info"
    )
    foreach ($metadataDirectory in $legacyMetadata) {
        if ($metadataDirectory.Parent.FullName -ne $pythonSitePackages) {
            throw "Legacy wrapper metadata is outside site-packages."
        }
        Remove-Item -LiteralPath $metadataDirectory.FullName -Recurse -Force
    }
    if (Get-ChildItem `
        -LiteralPath $pythonSitePackages `
        -Directory `
        -Filter "totalsegmentator_wrapper_mac-*.dist-info"
    ) {
        throw "Legacy wrapper distribution metadata remains."
    }

    $legalRoot = Join-Path $portableRoot "legal"
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

    Copy-Item `
        (Join-Path $repoRoot "docs\README_PORTABLE_JA.md") `
        (Join-Path $portableRoot "README_PORTABLE_JA.md")
    [pscustomobject]@{
        schema =
            "totalsegmentator_wrapper.windows_alpha_portable_payload.v1"
        package_version = $Version
        architecture = "x64"
        entrypoint = "tswm-windows-shell.exe"
        extraction_required = $true
        administrator_required = $false
        certificate_registration_required = $false
        install_required = $false
        results_location = "user_selected_or_local_app_data"
        distribution_directory_writable = $false
        bundled_totalsegmentator_datasets = $requiredDatasets
        bundled_additional_models = @()
    } |
        ConvertTo-Json -Depth 5 |
        Set-Content `
            -LiteralPath (Join-Path $portableRoot "portable-manifest.json") `
            -Encoding utf8

    $portableSelfTest = Join-Path `
        $evidenceRoot `
        "portable-self-test.json"
    $selfTestProcess = Start-Process `
        -FilePath (Join-Path $portableRoot "tswm-windows-shell.exe") `
        -ArgumentList @("--portable-self-test", $portableSelfTest) `
        -Wait `
        -PassThru `
        -WindowStyle Hidden
    if ($selfTestProcess.ExitCode -ne 0) {
        throw "Portable runtime and model self-test failed."
    }
    $selfTestPayload = Get-Content `
        -LiteralPath $portableSelfTest `
        -Raw |
        ConvertFrom-Json
    if ($selfTestPayload.status -ne "pass") {
        throw "Portable runtime and model evidence did not pass."
    }

    $supervisorEvidence = Join-Path `
        $evidenceRoot `
        "supervisor-self-test.json"
    Invoke-Checked "Job Object supervisor self-test" {
        & (Join-Path $portableRoot "tswm-process-supervisor.exe") `
            self-test `
            --evidence $supervisorEvidence
    }
    Invoke-Checked "portable pip check" {
        & $stagedPython -m pip check
    }

    $runtimeDiagnostic = Join-Path `
        $evidenceRoot `
        "runtime-diagnostic.json"
    Invoke-Checked "portable runtime diagnostic" {
        & $stagedPython `
            (Join-Path `
                $repoRoot `
                "scripts\write_portable_runtime_diagnostic.py") `
            --output $runtimeDiagnostic `
            --totalseg-home (Join-Path $portableRoot "models\totalseg-home") `
            --cuda-index 0
    }
    $diagnosticPayload = Get-Content `
        -LiteralPath $runtimeDiagnostic `
        -Raw |
        ConvertFrom-Json
    if ($diagnosticPayload.status -ne "pass") {
        throw "Portable runtime diagnostic evidence did not pass."
    }

    $payloadMeasure = Get-ChildItem $portableRoot -File -Recurse |
        Measure-Object Length -Sum
    $zipFileName =
        "TotalSegmentatorWrapperForWin-Alpha-Portable_{0}_win-x64.zip" -f
        $Version
    $zipPath = Join-Path $absoluteOutput $zipFileName
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::CreateFromDirectory(
        $portableRoot,
        $zipPath,
        [IO.Compression.CompressionLevel]::Optimal,
        $true
    )
    if (-not (Test-Path -LiteralPath $zipPath -PathType Leaf)) {
        throw "The portable ZIP was not created."
    }

    $manualOutput = Join-Path $absoluteOutput "README_PORTABLE_JA.md"
    Copy-Item `
        (Join-Path $repoRoot "docs\README_PORTABLE_JA.md") `
        $manualOutput `
        -Force
    $zipHash = Get-FileHash $zipPath -Algorithm SHA256
    $runtimeDevice = $diagnosticPayload.device
    $buildManifestPath = Join-Path `
        $absoluteOutput `
        "build-manifest.json"
    [pscustomobject]@{
        schema =
            "totalsegmentator_wrapper.windows_alpha_portable_build.v1"
        status = "pass"
        package_version = $Version
        architecture = "x64"
        zip_file = $zipFileName
        zip_bytes = (Get-Item $zipPath).Length
        zip_sha256 = $zipHash.Hash.ToLowerInvariant()
        extracted_file_count = $payloadMeasure.Count
        extracted_bytes = $payloadMeasure.Sum
        administrator_required = $false
        powershell_required = $false
        certificate_registration_required = $false
        install_required = $false
        private_key_distributed = $false
        distribution_directory_writable = $false
        results_location = "user_selected_or_local_app_data"
        python_runtime_network_resolution = $false
        dotnet_runtime_package_network_resolution = $false
        dotnet_runtime_packages = @($dotNetPackageEvidence)
        bundled_totalsegmentator_datasets = $requiredDatasets
        bundled_additional_models = @()
        portable_self_test = "pass"
        job_object_supervisor_self_test = "pass"
        pip_check = "pass"
        production_imports = "pass"
        strict_cuda_smoke = $runtimeDevice.status
        requested_device = $runtimeDevice.requested_device
        actual_device = $runtimeDevice.actual_device
        fallback_reason = $runtimeDevice.fallback_reason
        python = $diagnosticPayload.python
        torch = $diagnosticPayload.torch
        torch_cuda_build = $diagnosticPayload.torch_cuda_build
        totalsegmentator = $diagnosticPayload.totalsegmentator
        gpu = $runtimeDevice.device_name
        driver = $runtimeDevice.driver_version
        windows_10_extracted_payload = "pass"
        windows_11 = "unverified"
        clean_machine = "unverified"
    } |
        ConvertTo-Json -Depth 8 |
        Set-Content `
            -LiteralPath $buildManifestPath `
            -Encoding utf8

    $hashTargets = @(
        $zipPath,
        $manualOutput,
        $buildManifestPath
    )
    $hashLines = foreach ($target in $hashTargets) {
        $hash = Get-FileHash -LiteralPath $target -Algorithm SHA256
        "{0}  {1}" -f
            $hash.Hash.ToLowerInvariant(),
            (Split-Path -Leaf $target)
    }
    Set-Content `
        -LiteralPath (Join-Path $absoluteOutput "SHA256SUMS.txt") `
        -Value $hashLines `
        -Encoding ascii

    Write-Output $zipPath
}
finally {
    $env:TEMP = $oldTemp
    $env:TMP = $oldTmp
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = $oldDotnetTelemetry
    $env:DOTNET_NOLOGO = $oldDotnetNoLogo
    $env:DOTNET_CLI_HOME = $oldDotnetHome
    $env:PIP_CACHE_DIR = $oldPipCache
    $env:PYTHONDONTWRITEBYTECODE = $oldPythonBytecode
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
