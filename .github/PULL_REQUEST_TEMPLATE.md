## What changed

<!-- Describe the smallest coherent change. -->

## Why

<!-- Explain the concrete user, reliability, or maintenance need. -->

## Verification

<!-- List exact commands and PASS/FAIL/UNVERIFIED results. -->

## Checklist

- [ ] No patient data, DICOM, CT, masks, secrets, usernames, or unnecessary absolute paths
- [ ] New dependencies/assets include license and provenance review
- [ ] Relevant tests and `git diff --check` pass
- [ ] Real CUDA/native/installer items not executed are marked UNVERIFIED
- [ ] No silent CPU fallback or silent model/ROI/resolution change
