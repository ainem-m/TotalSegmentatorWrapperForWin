# Windows alpha on-demand model delivery verification

Date: 2026-08-01

Host scope: Windows 10 x64 engineering host

Status: implementation and local packaging candidate pass; distribution is
blocked until a real HTTPS model bundle location is approved.

## Implemented contract

- WPF, Job Object supervisor, DICOM binaries, bundled Sample 1, app-private
  Python 3.12.10, PyTorch 2.11.0+cu126, CUDA runtime, and TotalSegmentator
  2.14.0 remain in the portable ZIP.
- Only the two required TotalSegmentator model datasets are on demand.
- The build injects an exact HTTPS URL, bundle version, byte size, SHA-256,
  archive root, and required dataset list into a fixed manifest.
- Downloads use a user-writable LocalAppData model area. A matching `.part`
  and hashed URL metadata are retained after interruption.
- Resume requires HTTP 206 and a `Content-Range` beginning at the exact saved
  byte offset. An incompatible response is never appended to the partial.
- Exact byte size and SHA-256 are checked before extraction. Archive traversal,
  missing checkpoints, changed dataset declarations, enabled usage statistics,
  or `fallback_allowed` other than false are rejected.
- Extraction occurs in a new staging directory. The model becomes current only
  after validation and atomic promotion. Failure does not start CPU or another
  model.
- WPF receives only UTF-8 structured progress and a PHI-safe terminal result.
  URLs, local paths, stderr, and raw process output are not shown.

## Measured candidate artifacts

Model bundle candidate:

- file: `totalseg-craniofacial-models-1.0.0.zip`
- bytes: `365755104`
- SHA-256: `03907c8ac0ea890f919a4ef9fc813e449f3365ae63693c50955cfaa99fafdaaa`
- extracted model bytes: `413959450`
- datasets: `Dataset115_mandible`,
  `Dataset297_TotalSegmentator_total_3mm_1559subj`

Local full-bundle activation passed SHA-256 verification, safe extraction,
required-file validation, ready-marker creation, atomic promotion, archive
cleanup, and reported `resumed=true` without a network request by reusing a
complete verified partial.

The pre-distribution portable packaging candidate was:

- file: `TSW-Alpha-0.1.0.3-ondemand-win-x64.zip`
- bytes: `3081617188`
- SHA-256: `81482c9926a041c107108416ac94db400a0b462cab08b2ca26964654c527c7db`
- extracted bytes: `5533866781`
- checkpoint files in ZIP: `0`
- model manifests in ZIP: `1`
- `model_delivery`: `ondemand`

This is about 365.7 MB smaller than the complete offline ZIP. The app-private
runtime remains the dominant size, so model-only on-demand delivery is not a
small bootstrap installer.

The candidate contains the reserved non-routable placeholder host
`models.example.invalid`. It is evidence for packaging mechanics only and must
not be given to testers. Rebuild after the approved HTTPS URL is known.

## Checks

| Check | Result |
| --- | --- |
| interrupted partial retained | PASS |
| retry sends exact HTTP Range offset | PASS |
| resumed progress is structured | PASS |
| complete partial revalidated without download | PASS |
| SHA-256 mismatch blocks promotion | PASS |
| path traversal blocks promotion | PASS |
| PowerShell UTF-8 BOM manifest | PASS |
| real model bundle validation and atomic activation | PASS |
| WPF model progress/result JSON contract | PASS |
| WPF Release build | PASS, 0 warnings / 0 errors |
| ProcessSupervisor Release build | PASS, 0 warnings / 0 errors |
| Python suite | PASS, 225 tests / 3 skipped |
| `git diff --check` | PASS |
| candidate portable self-test | PASS |
| candidate Job Object self-test | PASS |
| candidate `pip check` and production imports | PASS |
| candidate strict `cuda:0` smoke | PASS, no fallback |

## Unverified and blocking

- approved HTTPS hosting location and access policy
- manifest signing or another authenticity mechanism beyond the bundled
  SHA-256 manifest
- real interrupted transfer and resume against the final hosting server
- WPF end-to-end download from that server
- on-demand model followed by real Sample 1 inference from the user model area
- clean-machine and Windows 11
- update, rollback, installer, signing, and Store distribution

The complete offline 0.1.0.2 ZIP remains the tester-ready alpha package.
