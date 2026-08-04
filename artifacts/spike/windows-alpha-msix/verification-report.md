# Windows alpha MSIX verification

Date: 2026-07-31
Host: Windows 10 IoT Enterprise 22H2, build 19045.6456

## Result

The self-signed alpha MSIX build and unpacked-payload verification are PASS.
Machine-level certificate trust, installed-package launch, and uninstall remain
UNVERIFIED because the required UAC elevation was cancelled.

This is an invited, non-clinical alpha package. It is not a Store or production
release.

## Distribution candidate

- Identity: `TotalSegmentatorWrapperForWin.Alpha`
- Version: `0.1.0.0`
- Architecture: `x64`
- Size: `3510370099` bytes
- SHA-256:
  `ae93ba2269d3f28a38d5f53d5dbb64548afd6b2a740afc26ef7f2c9b70126aa0`
- Publisher: `CN=TotalSegmentatorWrapperForWin Alpha`
- Certificate thumbprint:
  `A5A68377BB4FB23679DE9F300FBF6E2EF58EA7E7`
- Certificate expiry: `2027-07-30T22:35:13Z`
- Private key/PFX distributed: no

The binary distribution is kept outside Git. The repository contains the
build, install, uninstall, license-inventory, and contract-test sources only.

## PASS

- Official WinApp CLI `0.5.0` and Windows MakeAppx produced and validated the
  package.
- The package was signed with SHA-256 and the embedded signer thumbprint
  matches the bundled public certificate.
- The only Authenticode chain status before machine trust is the expected
  `UntrustedRoot`; hash mismatch and signer mismatch are not accepted.
- Python installation is binary-only/offline and `pip check` reports no broken
  requirements.
- .NET self-contained restore uses only the pinned local `10.0.10` runtime-pack
  feed. All three Microsoft nupkg author and repository signatures passed
  `dotnet nuget verify --all`.
- Runtime license inventory: PASS, 92 distributions, no unresolved entry.
- No PFX, `.key`, or private-key-like PEM remains in the package.
- No legacy `totalsegmentator_wrapper_mac-*.dist-info` remains.
- Bundled non-empty checkpoints:
  - `Dataset115_mandible`: `247186029` bytes
  - `Dataset297_TotalSegmentator_total_3mm_1559subj`: `164939235` bytes
- Bundled NIfTI sample, local offline preview, DICOM normalizer, and dcm2niix
  are present.
- WPF package payload contract self-test: exit `0`.
- Job Object supervisor package payload self-test: PASS, active processes `0`,
  no survivors.
- Strict CUDA package payload smoke: PASS on `cuda:0`.
  - NVIDIA GeForce RTX 2060
  - driver `572.83`
  - Python `3.12.10`
  - PyTorch `2.11.0+cu126`
  - CUDA build `12.6`
  - Conv3d, normalization, activation, ConvTranspose3d, synchronize, and finite
    output: PASS
- Python tests: 216 PASS, 3 skipped.
- CoordinatorShell Release build: PASS, 0 warnings/errors.
- ProcessSupervisor Release build: PASS, 0 warnings/errors.
- `git diff --check`: PASS.

## UNVERIFIED

- Importing the public certificate into
  `LocalMachine\TrustedPeople` requires administrator elevation. Microsoft
  documents that App Installer checks the machine store for self-signed MSIX.
- Actual `Add-AppxPackage` success after machine trust.
- Installed Start-menu launch and installed-package runtime discovery.
- Installed-package uninstall and exact certificate removal.
- Clean-machine installation.
- Windows 11 installation and execution.
- Store/trusted production signing.
- Update and rollback.
- Exact packaged TotalSegmentator sample inference was not repeated; the
  already-verified app-private runtime/model payload was reused and the exact
  packaged payload passed imports and strict CUDA smoke.
- DentalSegmentator, Individual Teeth, and ToothSeg checkpoints are not
  included in this first alpha.

## Next required action

On a dedicated alpha test machine, run the included install script from an
elevated PowerShell window, launch the app once, run bundled Sample 1, then run
the included uninstall script with `-RemoveTrustedCertificate`. Record install,
launch, CUDA inference, uninstall, package removal, and certificate removal
before declaring the installer validated.
