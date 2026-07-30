# Repository provenance

This repository was initialized as a Windows-focused source snapshot from:

- source repository: `ainem-m/segmentation_w_mps`
- source branch: `agent/windows-shell-refactor-prune`
- source commit: `62194420daaabe4d471dfc81418e25a74d708ef9`
- snapshot date: 2026-07-31

The snapshot retains the Windows WPF shell, Job Object supervisor, native DICOM
normalizer, shared Python coordinator/backend, non-clinical sample resources,
third-party notices, Windows engineering evidence, and relevant tests.

The macOS Swift application, DMG/notarization/update pipeline, Cloudflare
distribution project, and Mac-only build scripts/tests were intentionally
excluded. The internal Python namespace was retained to preserve protocol and
artifact compatibility; it does not indicate platform support in this
repository.

No git history was copied into the new repository. This prevents unrelated
macOS distribution history and historical artifacts from becoming part of the
Windows publication boundary. Original authorship and license notices remain
available in the source repository and retained files.
