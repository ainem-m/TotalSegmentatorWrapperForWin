# Windows alpha portable ZIP verification

Date: 2026-07-31

Host scope: Windows 10 x64 engineering host

Distribution version: 0.1.0.0

## Package

- ZIP: `TotalSegmentatorWrapperForWin-Alpha-Portable_0.1.0.0_win-x64.zip`
- ZIP bytes: `3450825350`
- ZIP SHA-256: `49a310acba35a5865dbc08c0a95f792f886a83a37ad9671434b67b7806e043fa`
- Extracted files: `41954`
- Extracted bytes: `5947842035` (about 5.54 GiB)
- Administrator, PowerShell, certificate registration, and installation required: no
- Python or .NET dependency resolution from a public index: no
- Private key, PFX, or key-like PEM in the ZIP: none
- Runtime and result writes to the extracted distribution: none

The final ZIP was extracted into a new directory. After WPF diagnostics,
Python diagnostics, DICOM probes, and real Sample 1 inference, every extracted
file was compared with the ZIP entry by relative path, size, and CRC. All
`41954` files matched, and there were no added files.

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
| Extracted WPF startup/self-test | PASS | runtime/model, DICOM binary, archive guard, and user-output checks passed |
| ZIP-direct-launch guard contract | PASS | archive path is rejected with extraction guidance |
| Job Object supervisor self-test | PASS | suspended creation, assign-before-resume, termination, and no survivors |
| `pip check` | PASS | no broken requirements |
| Production imports | PASS | torch, nibabel, scipy, scikit-image, TotalSegmentator, coordinator, and runner |
| Strict `cuda:0` smoke | PASS | requested and actual device were `cuda:0`; no fallback |
| Bundled Sample 1 | PASS | real TotalSegmentator `craniofacial_structures` completed in 102.4 seconds |
| Coordinator terminal/exit | PASS | one `operation_completed`; supervisor/coordinator exit code `0` |
| Job/GPU process cleanup | PASS | active Job process count `0`; no portable GPU process remained |
| Staging promotion | PASS | verified output promoted; staging absent |
| Artifact manifest | PASS | all 14 manifest entries matched size and SHA-256 |
| NIfTI masks | PASS | 7 masks found; 6 were non-empty |
| Offline preview | PASS | local assets only; no HTTP(S) or `file://` references |
| DICOM binaries | PASS | normalizer `0.3.0` doctor passed with GDCM `3.2.6`; dcm2niix `v1.0.20260724` help probe exited `0` |
| Distribution directory unchanged | PASS | all 41954 ZIP entries matched after inference |
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

TotalSegmentator model weights remained in the extracted read-only payload.
Its mutable `config.json` was copied to the application-specific LocalAppData
state directory, with usage statistics disabled, and was updated only there.

## Unverified

- Windows 11
- clean-machine extraction and launch
- SmartScreen behavior on tester machines
- GPU and driver combinations other than the measured host
- trusted code signing and Microsoft Store submission
- update and rollback

This is an invited-alpha portable runtime result, not a clinical validation or
a completed Windows product release.
