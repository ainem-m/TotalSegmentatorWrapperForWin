# Release status

## Current designation

Engineering alpha / source release.

## Verified on Windows 10 x64

- binary-only, hash-locked Python dependency closure
- strict NVIDIA CUDA device doctor and negative tests
- real TotalSegmentator `craniofacial_structures` sample inference
- coordinator JSONL/staging/artifact verification
- .NET Job Object normal completion and cancellation
- WPF coordinator vertical slice
- native DICOM/MSVC clean and Secondary Capture rescue paths
- bundled sample, non-empty NIfTI masks, local offline preview

Measured engineering host details are recorded under
`artifacts/spike/windows-runtime-cuda/` and
`artifacts/spike/windows-mac-parity-closeout/`.

## Not release-complete

- Windows 11 validation
- clean-machine installation
- invited-alpha machine-level MSIX installation and uninstall validation
- trusted production or Store code signing
- update and rollback
- redistribution approval for every runtime binary and model
- external UI Automation, high contrast, and non-96-DPI validation

These items must remain `UNVERIFIED`; source publication is not evidence that
the Windows product is complete.
