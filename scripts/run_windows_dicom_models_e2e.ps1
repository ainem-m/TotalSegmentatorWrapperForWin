[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ShellExe,

    [Parameter(Mandatory)]
    [string]$EngineeringConfig,

    [Parameter(Mandatory)]
    [string]$DicomFolder,

    [Parameter(Mandatory)]
    [string]$EvidenceDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-AbsoluteExistingPath {
    param(
        [string]$Path,
        [string]$Name
    )

    if (-not [System.IO.Path]::IsPathFullyQualified($Path)) {
        throw "$Name must be an absolute path."
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Name was not found: $Path"
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

$shellPath = Require-AbsoluteExistingPath $ShellExe "ShellExe"
$configPath = Require-AbsoluteExistingPath $EngineeringConfig "EngineeringConfig"
$dicomPath = Require-AbsoluteExistingPath $DicomFolder "DicomFolder"
if (-not [System.IO.Path]::IsPathFullyQualified($EvidenceDirectory)) {
    throw "EvidenceDirectory must be an absolute path."
}
$evidenceRoot = [System.IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Force -Path $evidenceRoot | Out-Null

$models = @(
    @{ Name = "totalseg"; Operation = "run_nifti_totalsegmentator" },
    @{ Name = "dentalseg"; Operation = "run_nifti_dentalsegmentator" },
    @{ Name = "toothseg"; Operation = "run_nifti_toothseg" }
)

foreach ($model in $models) {
    $evidencePath = Join-Path $evidenceRoot "$($model.Name)-evidence.json"
    $startedAt = Get-Date
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $shellPath
    $startInfo.UseShellExecute = $false
    foreach ($argument in @(
        "--engineering-config",
        $configPath,
        "--evidence-run-dicom-model",
        $model.Name,
        $dicomPath,
        $evidencePath
    )) {
        [void]$startInfo.ArgumentList.Add($argument)
    }

    $process = [System.Diagnostics.Process]::Start($startInfo)
    if ($null -eq $process) {
        throw "Failed to start the Windows shell for $($model.Name)."
    }
    $process.WaitForExit()

    if (-not (Test-Path -LiteralPath $evidencePath)) {
        throw "The $($model.Name) evidence file was not created."
    }
    $evidenceItem = Get-Item -LiteralPath $evidencePath
    if ($evidenceItem.LastWriteTime -lt $startedAt) {
        throw "The $($model.Name) evidence file was not updated by this run."
    }
    $evidence = Get-Content -LiteralPath $evidencePath -Raw |
        ConvertFrom-Json
    $passed =
        $process.ExitCode -eq 0 -and
        $evidence.status -eq "pass" -and
        $evidence.source_kind -eq "dicom" -and
        $evidence.operation -eq $model.Operation -and
        $evidence.terminal_event -eq "operation_completed" -and
        $evidence.supervisor_exit_code -eq 0 -and
        $evidence.requested_policy -eq "cuda_required" -and
        $evidence.requested_device_index -eq 0 -and
        $evidence.resolved_device -eq "cuda:0" -and
        -not $evidence.fallback_allowed -and
        -not $evidence.fallback_occurred -and
        $evidence.mpr_preview_verified -and
        $evidence.run_manifest_verified -and
        $evidence.artifact_manifest_exists -and
        $evidence.offline_preview_exists
    if (-not $passed) {
        throw "The $($model.Name) DICOM E2E evidence did not pass: $evidencePath"
    }
    Write-Host "$($model.Name): pass"
}
