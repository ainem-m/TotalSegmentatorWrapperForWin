# Third-party notices

This repository contains integration code, notices, and non-clinical sample
assets related to third-party projects. It does not relicense third-party
software, model checkpoints, or trademarks under this repository's
Apache-2.0 license.

Primary integrations include:

- [TotalSegmentator](https://github.com/wasserth/TotalSegmentator)
- [SlicerDentalSegmentator](https://github.com/gaudot/SlicerDentalSegmentator)
- [ToothSeg](https://github.com/MIC-DKFZ/ToothSeg)
- [GDCM](https://github.com/malaterre/GDCM)
- [dcm2niix](https://github.com/rordenlab/dcm2niix)
- Python, PyTorch, nnU-Net, 3D Slicer, and their transitive dependencies

Detailed license texts and provenance records are stored in
[`resources/third_party/`](resources/third_party/). Sample-specific notices are
stored in [`resources/sample1/`](resources/sample1/).

Model weights, the internal Windows wheelhouse, NVIDIA components, and
app-private runtime binaries are intentionally not included in this source
repository. Anyone distributing a binary build must independently verify the
licenses and redistribution terms for every bundled component and model.
