# Windows alpha portable ZIP verification

Date: 2026-07-31

Host scope: Windows 10 x64 engineering host

Distribution version: 0.1.0.0

## Package

- ZIP: `TSW-Alpha-0.1.0.0-win-x64.zip`
- ZIP bytes: `3447349790`
- ZIP SHA-256: `4ca6fb5176d36c2733725d02e450ac86700a926c1d9adc50aa9ec20e7491fb43`
- Extracted files: `41953`
- Extracted bytes: `5947770212` (about 5.54 GiB)
- Maximum ZIP-internal file path: `177` characters
- Longest path in the verification extraction: `223` characters
- Administrator, PowerShell, certificate registration, and installation required: no
- Python or .NET dependency resolution from a public index: no
- Private key, PFX, or key-like PEM in the ZIP: none
- Runtime and result writes to the extracted distribution: none

The final ZIP was extracted into a new directory. After WPF diagnostics,
Python diagnostics, DICOM probes, and real Sample 1 inference, all `41953`
relative paths and sizes still matched the ZIP, no files had been added, and
no payload file had a post-extraction modification time.

The extracted root contains exactly one executable:
`START_HERE_TotalSegmentatorWrapperForWin.exe`. The headless Job Object
supervisor is under `runtime/native` and is not presented as a launcher.

## Runtime

- Python: `3.12.10`
- PyTorch: `2.11.0+cu126`
- PyTorch CUDA build: `12.6`
- TotalSegmentator: `2.14.0`
- GPU: `NVIDIA GeForce RTX 2060`
- Driver: `572.83`
- Compute capability: `7.5`
- Device memory: `6442123264` bytes

The strict CUDA tensor smoke passed tensor creation, Conv3d, normalization,
activation, ConvTranspose3d, synchronization, and finite-output checks on
`cuda:0`.

## Final ZIP checks

| Criterion | Result | Evidence |
| --- | --- | --- |
| Unambiguous launcher | PASS | exactly one root EXE; friendly file description/product/company metadata |
| Extracted WPF startup/self-test | PASS | runtime/model, DICOM binary, archive guard, and user-output checks passed |
| Windows path-length budget | PASS | short `TSW` root; maximum internal path 177; reported `dataset.json` extracted successfully |
| ZIP-direct-launch guard contract | PASS | archive path is rejected with extraction guidance |
| Job Object supervisor self-test | PASS | suspended creation, assign-before-resume, termination, and no survivors |
| `pip check` | PASS | no broken requirements |
| Production imports | PASS | torch, nibabel, scipy, scikit-image, TotalSegmentator, coordinator, and runner |
| Strict `cuda:0` smoke | PASS | requested and actual device were `cuda:0`; no fallback |
| Bundled Sample 1 | PASS | real TotalSegmentator `craniofacial_structures` completed from the short-path extraction |
| Coordinator terminal/exit | PASS | one `operation_completed`; supervisor/coordinator exit code `0` |
| Job/GPU process cleanup | PASS | active Job process count `0`; no portable GPU process remained |
| Staging promotion | PASS | verified output promoted; staging absent |
| Artifact manifest | PASS | all 14 manifest entries matched size and SHA-256 |
| NIfTI masks | PASS | 7 masks found; 6 were non-empty |
| Offline preview | PASS | local assets only; no HTTP(S) or `file://` references |
| DICOM binaries | PASS | normalizer `0.3.0` doctor passed with GDCM `3.2.6`; dcm2niix `v1.0.20260724` help probe exited `0` |
| Distribution directory unchanged | PASS | all 41953 paths and sizes matched; zero post-extraction modifications |
| Private key/PFX absence | PASS | zero key-like files |
| Python tests | PASS | 221 passed, 3 skipped |
| WPF Release build | PASS | 0 warnings, 0 errors |
| ProcessSupervisor Release build | PASS | 0 warnings, 0 errors |
| `git diff --check` | PASS | no whitespace errors |
| Existing macOS CLI/progress contracts | PASS | covered by the full Python suite |

The run manifest recorded:

- `requested_policy = cuda_required`
- `requested_device_index = 0`
- `resolved_device = cuda:0`
- `fallback_allowed = false`
- `fallback_occurred = false`

The final launcher run used operation
`b3ff8990-6e0c-4363-9b4e-e0a11b2f0057`. It emitted 23 valid JSONL events,
exactly one terminal `operation_completed`, no absolute path or third-party
output/tail in JSONL, and exited through the supervisor with OS exit code 0.

TotalSegmentator model weights remained in the extracted read-only payload.
Its mutable `config.json` was copied to the application-specific LocalAppData
state directory, with usage statistics disabled, and was updated only there.

## Unverified

- Windows 11
- clean-machine extraction and launch
- automated clicking of the Windows Explorer extraction dialog
- SmartScreen behavior on tester machines
- GPU and driver combinations other than the measured host
- trusted code signing and Microsoft Store submission
- update and rollback

This is an invited-alpha portable runtime result, not a clinical validation or
a completed Windows product release.
