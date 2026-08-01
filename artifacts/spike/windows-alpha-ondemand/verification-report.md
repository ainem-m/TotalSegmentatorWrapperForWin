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
- URL selected for upload:
  `https://downloads.lacramy.com/totalsegmentator-wrapper-win/models/1.0.0/totalseg-craniofacial-models-1.0.0.zip`
- bytes: `365760315`
- SHA-256: `ec48c1d62768055ef90d3250a041bb98167ecadbc3b1c495a284459d670e38e6`
- extracted model files: `19`
- extracted model bytes: `413971462`
- datasets: `Dataset115_mandible`,
  `Dataset297_TotalSegmentator_total_3mm_1559subj`
- legal files: upstream Apache-2.0 text, model bundle NOTICE, and the pinned
  TotalSegmentator task inventory

Local final-bundle activation passed SHA-256 verification, safe extraction,
required-model and legal-file validation, ready-marker creation, atomic
promotion, archive cleanup, and reported `resumed=true` without a network
request by reusing a complete verified partial.

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

That portable candidate contains the reserved non-routable placeholder host
`models.example.invalid` and predates the legal-file requirement. It is
evidence for packaging mechanics only, is superseded by the final model bundle,
and must not be given to testers. Rebuild the portable ZIP after R2 upload and
remote verification succeed.

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
| Apache-2.0 text, model NOTICE, and task inventory present | PASS |
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

- R2 upload and remote object immutability policy
- manifest signing or another authenticity mechanism beyond the bundled
  SHA-256 manifest
- real interrupted transfer and resume against the final hosting server
- WPF end-to-end download from that server
- on-demand model followed by real Sample 1 inference from the user model area
- clean-machine and Windows 11
- update, rollback, installer, signing, and Store distribution

The complete offline 0.1.0.2 ZIP remains the tester-ready alpha package.
