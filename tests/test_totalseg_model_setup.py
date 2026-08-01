from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from totalsegmentator_wrapper_mac.totalseg_model_setup import (
    ModelSetupError,
    install_model_bundle,
    load_model_manifest,
    model_status,
)


DATASETS = ["Dataset115_mandible", "Dataset297_TotalSegmentator_total_3mm_1559subj"]


class _Response:
    def __init__(self, payload: bytes, *, status: int, headers: dict[str, str], fail_after: int | None = None) -> None:
        self.payload = payload
        self.status = status
        self.headers = headers
        self.position = 0
        self.fail_after = fail_after

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def getcode(self) -> int:
        return self.status

    def read(self, size: int) -> bytes:
        if self.fail_after is not None and self.position >= self.fail_after:
            raise OSError("simulated interruption")
        chunk = self.payload[self.position : self.position + min(size, 64)]
        self.position += len(chunk)
        return chunk


class TotalSegModelSetupTests(unittest.TestCase):
    def test_manifest_accepts_powershell_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            payload = _manifest(b"bundle")
            path.write_text(json.dumps(payload), encoding="utf-8-sig")
            self.assertEqual(load_model_manifest(path), payload)

    def test_interrupted_download_resumes_and_promotes_only_after_hash_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "source.zip"
            _write_bundle(archive)
            payload = archive.read_bytes()
            manifest = _manifest(payload)
            model_root = root / "state" / "totalseg-home"

            first = _Response(payload, status=200, headers={"Content-Length": str(len(payload))}, fail_after=128)
            with patch("urllib.request.urlopen", return_value=first):
                with self.assertRaisesRegex(ModelSetupError, "再試行すると続きから再開"):
                    install_model_bundle(manifest=manifest, model_root=model_root)
            self.assertFalse(model_root.exists())
            partial = model_root.parent / "downloads" / "craniofacial-1.0.0.zip.part"
            self.assertGreater(partial.stat().st_size, 0)
            offset = partial.stat().st_size

            second = _Response(
                payload[offset:],
                status=206,
                headers={"Content-Range": f"bytes {offset}-{len(payload)-1}/{len(payload)}"},
            )
            output = io.StringIO()
            with patch("urllib.request.urlopen", return_value=second) as urlopen, redirect_stdout(output):
                result = install_model_bundle(manifest=manifest, model_root=model_root)

            request = urlopen.call_args.args[0]
            self.assertEqual(request.headers["Range"], f"bytes={offset}-")
            self.assertTrue(result["resumed"])
            self.assertFalse(result["fallback_allowed"])
            self.assertEqual(model_status(manifest=manifest, model_root=model_root)["status"], "ready")
            self.assertFalse(partial.exists())
            events = [
                json.loads(line.removeprefix("TOTALSEG_MODEL_PREP_PROGRESS "))
                for line in output.getvalue().splitlines()
                if line.startswith("TOTALSEG_MODEL_PREP_PROGRESS ")
            ]
            self.assertTrue(any(event.get("resumed") is True for event in events))
            self.assertEqual(events[-1]["stage"], "complete")

    def test_hash_mismatch_never_promotes_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "source.zip"
            _write_bundle(archive)
            payload = archive.read_bytes()
            manifest = _manifest(payload)
            manifest["sha256"] = "0" * 64
            response = _Response(payload, status=200, headers={"Content-Length": str(len(payload))})

            with patch("urllib.request.urlopen", return_value=response):
                with self.assertRaisesRegex(ModelSetupError, "検証できません") as caught:
                    install_model_bundle(manifest=manifest, model_root=root / "models")

            self.assertEqual(caught.exception.error_code, "model_hash_mismatch")
            self.assertFalse((root / "models").exists())

    def test_path_traversal_is_rejected_before_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "source.zip"
            _write_bundle(archive, unsafe=True)
            payload = archive.read_bytes()
            manifest = _manifest(payload)
            response = _Response(payload, status=200, headers={"Content-Length": str(len(payload))})
            with patch("urllib.request.urlopen", return_value=response):
                with self.assertRaisesRegex(ModelSetupError, "内容を確認"):
                    install_model_bundle(manifest=manifest, model_root=root / "models")
            self.assertFalse((root / "models").exists())


def _manifest(payload: bytes) -> dict[str, object]:
    return {
        "schema": "totalsegmentator_wrapper.windows_totalseg_model_bundle.v1",
        "bundle_id": "craniofacial",
        "version": "1.0.0",
        "url": "https://models.example.invalid/craniofacial-1.0.0.zip",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "archive_root": "totalseg-home",
        "datasets": DATASETS,
        "fallback_allowed": False,
    }


def _write_bundle(path: Path, *, unsafe: bool = False) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("totalseg-home/config.json", json.dumps({"send_usage_stats": False}))
        for dataset in DATASETS:
            archive.writestr(f"totalseg-home/nnunet/results/{dataset}/trainer/fold_0/checkpoint_final.pth", b"weights")
        if unsafe:
            archive.writestr("totalseg-home/../../escaped.txt", "no")


if __name__ == "__main__":
    unittest.main()
