from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
from pathlib import Path


REQUIRED_DATASETS = (
    "Dataset115_mandible",
    "Dataset297_TotalSegmentator_total_3mm_1559subj",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--totalseg-home", required=True, type=Path)
    parser.add_argument("--cuda-index", default=0, type=int)
    args = parser.parse_args()

    import nibabel
    import scipy
    import skimage
    import torch
    import totalsegmentator
    import totalsegmentator_wrapper_mac.coordinator
    import totalsegmentator_wrapper_mac.runner_totalseg
    from totalsegmentator_wrapper_mac.device import smoke_test_cuda

    del (
        nibabel,
        scipy,
        skimage,
        totalsegmentator,
        totalsegmentator_wrapper_mac,
    )

    model_checks = []
    models_pass = True
    for dataset in REQUIRED_DATASETS:
        dataset_root = (
            args.totalseg_home / "nnunet" / "results" / dataset
        )
        checkpoints = [
            path
            for path in dataset_root.rglob("checkpoint_final.pth")
            if path.is_file() and path.stat().st_size > 0
        ]
        passed = dataset_root.is_dir() and bool(checkpoints)
        models_pass = models_pass and passed
        model_checks.append(
            {
                "dataset": dataset,
                "status": "pass" if passed else "fail",
                "checkpoint_count": len(checkpoints),
                "checkpoint_bytes": sum(
                    path.stat().st_size for path in checkpoints
                ),
            }
        )

    cuda = smoke_test_cuda(args.cuda_index).to_dict()
    passed = models_pass and cuda["status"] == "pass"
    payload = {
        "schema": (
            "totalsegmentator_wrapper.windows_portable_runtime_diagnostic.v1"
        ),
        "status": "pass" if passed else "fail",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "totalsegmentator": importlib.metadata.version("TotalSegmentator"),
        "production_imports": "pass",
        "models": model_checks,
        "device": cuda,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": payload["status"], "schema": payload["schema"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
