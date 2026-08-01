[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TotalSegmentatorHome,
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^https://")]
    [string]$BundleUri,
    [ValidatePattern("^\d+\.\d+\.\d+$")]
    [string]$Version = "1.0.0"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$source = (Resolve-Path -LiteralPath $TotalSegmentatorHome).Path
$output = [IO.Path]::GetFullPath($OutputDirectory)
$datasets = @(
    "Dataset115_mandible",
    "Dataset297_TotalSegmentator_total_3mm_1559subj"
)
$config = Join-Path $source "config.json"
if (-not (Test-Path -LiteralPath $config -PathType Leaf)) {
    throw "TotalSegmentator config.json was not found."
}
$configPayload = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
if ($configPayload.send_usage_stats -ne $false) {
    throw "TotalSegmentator usage statistics must be disabled."
}
foreach ($dataset in $datasets) {
    $datasetRoot = Join-Path $source "nnunet\results\$dataset"
    $checkpoint = Get-ChildItem `
        -LiteralPath $datasetRoot `
        -Filter "checkpoint_final.pth" `
        -File `
        -Recurse `
        -ErrorAction Stop |
        Where-Object Length -gt 0 |
        Select-Object -First 1
    if ($null -eq $checkpoint) {
        throw "A required TotalSegmentator checkpoint was not found."
    }
}

New-Item -ItemType Directory -Path $output -Force | Out-Null
$buildId = [Guid]::NewGuid().ToString("N")
$staging = Join-Path $output ".bundle-staging-$buildId"
$bundleRoot = Join-Path $staging "totalseg-home"
$zipName = "totalseg-craniofacial-models-$Version.zip"
$zipPath = Join-Path $output $zipName
try {
    New-Item -ItemType Directory -Path $bundleRoot -Force | Out-Null
    Copy-Item -LiteralPath $config -Destination $bundleRoot
    foreach ($dataset in $datasets) {
        $destination = Join-Path $bundleRoot "nnunet\results\$dataset"
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
        & robocopy `
            (Join-Path $source "nnunet\results\$dataset") `
            $destination `
            /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /MT:16 `
            /NFL /NDL /NJH /NJS /NP
        if ($LASTEXITCODE -gt 7) {
            throw "Model bundle copy failed."
        }
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    [IO.Compression.ZipFile]::CreateFromDirectory(
        $staging,
        $zipPath,
        [IO.Compression.CompressionLevel]::Optimal,
        $false
    )
    $hash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $manifest = [ordered]@{
        schema =
            "totalsegmentator_wrapper.windows_totalseg_model_bundle.v1"
        bundle_id = "craniofacial"
        version = $Version
        url = $BundleUri
        sha256 = $hash
        size_bytes = (Get-Item -LiteralPath $zipPath).Length
        archive_root = "totalseg-home"
        datasets = $datasets
        fallback_allowed = $false
    }
    $manifestPath = Join-Path $output "totalseg-model-bundle.json"
    $manifest | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath $manifestPath -Encoding utf8
    Write-Output $manifestPath
}
finally {
    if (Test-Path -LiteralPath $staging) {
        Remove-Item -LiteralPath $staging -Recurse -Force
    }
}
