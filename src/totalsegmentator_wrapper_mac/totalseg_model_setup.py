from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4


MANIFEST_SCHEMA = "totalsegmentator_wrapper.windows_totalseg_model_bundle.v1"
OFFICIAL_ASSETS_MANIFEST_SCHEMA = (
    "totalsegmentator_wrapper.windows_totalseg_official_assets.v1"
)
PYTORCH_RUNTIME_MANIFEST_SCHEMA = (
    "totalsegmentator_wrapper.windows_pytorch_runtime_bundle.v1"
)
READY_SCHEMA = "totalsegmentator_wrapper.windows_totalseg_model_ready.v1"
PYTORCH_RUNTIME_READY_SCHEMA = (
    "totalsegmentator_wrapper.windows_pytorch_runtime_ready.v1"
)
SETUP_SCHEMA = "totalsegmentator_wrapper.windows_totalseg_model_setup.v1"
PROGRESS_PREFIX = "TOTALSEG_MODEL_PREP_PROGRESS "
CHUNK_SIZE = 1024 * 1024
REQUIRED_DATASETS = [
    "Dataset115_mandible",
    "Dataset297_TotalSegmentator_total_3mm_1559subj",
]
REQUIRED_LEGAL_FILES = [
    "TotalSegmentator-Apache-2.0.txt",
    "TotalSegmentator-model-bundle-NOTICE.txt",
    "totalsegmentator_task_inventory.json",
]
PYTORCH_RUNTIME_BUNDLE_ID = "pytorch-cuda"
PYTORCH_RUNTIME_VERSION = "2.11.0+cu126-cp312-win-x64"
PYTORCH_RUNTIME_PACKAGE = "torch"
PYTORCH_RUNTIME_PYTHON_VERSION = "3.12"
PYTORCH_RUNTIME_TORCH_VERSION = "2.11.0+cu126"
PYTORCH_RUNTIME_CUDA_VERSION = "12.6"
PYTORCH_RUNTIME_WHEEL_FILENAME = (
    "torch-2.11.0+cu126-cp312-cp312-win_amd64.whl"
)
PYTORCH_RUNTIME_URL_PREFIX = "https://download.pytorch.org/whl/cu126/"


class ModelSetupError(RuntimeError):
    def __init__(self, error_code: str, safe_reason: str) -> None:
        super().__init__(safe_reason)
        self.error_code = error_code
        self.safe_reason = safe_reason


def load_model_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelSetupError(
            "model_manifest_invalid",
            "モデル取得情報を確認できませんでした。",
        ) from exc
    if (
        isinstance(payload, dict)
        and payload.get("schema") == OFFICIAL_ASSETS_MANIFEST_SCHEMA
    ):
        return _load_official_assets_manifest(payload)
    if not isinstance(payload, dict) or payload.get("schema") != MANIFEST_SCHEMA:
        raise ModelSetupError("model_manifest_invalid", "モデル取得情報を確認できませんでした。")
    required_strings = ("bundle_id", "version", "url", "sha256", "archive_root")
    if any(not isinstance(payload.get(key), str) or not payload[key] for key in required_strings):
        raise ModelSetupError("model_manifest_invalid", "モデル取得情報を確認できませんでした。")
    if not payload["url"].lower().startswith("https://"):
        raise ModelSetupError("model_manifest_invalid", "モデルの取得元がHTTPSではありません。")
    if len(payload["sha256"]) != 64 or any(character not in "0123456789abcdef" for character in payload["sha256"].lower()):
        raise ModelSetupError("model_manifest_invalid", "モデル取得情報を確認できませんでした。")
    if not isinstance(payload.get("size_bytes"), int) or payload["size_bytes"] <= 0:
        raise ModelSetupError("model_manifest_invalid", "モデル取得情報を確認できませんでした。")
    datasets = payload.get("datasets")
    if (
        datasets != REQUIRED_DATASETS
        or payload.get("legal_files") != REQUIRED_LEGAL_FILES
        or payload["archive_root"] != "totalseg-home"
        or payload.get("fallback_allowed") is not False
    ):
        raise ModelSetupError("model_manifest_invalid", "モデル取得情報を確認できませんでした。")
    return payload


def _load_official_assets_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    required_strings = ("bundle_id", "version", "sha256")
    if any(
        not isinstance(payload.get(key), str) or not payload[key]
        for key in required_strings
    ):
        raise ModelSetupError("model_manifest_invalid", "Official model manifest is invalid.")
    if (
        len(payload["sha256"]) != 64
        or any(
            character not in "0123456789abcdef"
            for character in payload["sha256"].lower()
        )
        or not isinstance(payload.get("size_bytes"), int)
        or payload["size_bytes"] <= 0
        or payload.get("datasets") != REQUIRED_DATASETS
        or payload.get("legal_files") != REQUIRED_LEGAL_FILES
        or payload.get("fallback_allowed") is not False
    ):
        raise ModelSetupError("model_manifest_invalid", "Official model manifest is invalid.")
    assets = payload.get("assets")
    if not isinstance(assets, list) or len(assets) != len(REQUIRED_DATASETS):
        raise ModelSetupError("model_manifest_invalid", "Official model manifest is invalid.")
    for dataset, asset in zip(REQUIRED_DATASETS, assets, strict=True):
        if (
            not isinstance(asset, dict)
            or asset.get("dataset") != dataset
            or asset.get("archive_root") != dataset
            or not isinstance(asset.get("url"), str)
            or not asset["url"].startswith(
                "https://github.com/wasserth/TotalSegmentator/releases/download/"
            )
            or not isinstance(asset.get("sha256"), str)
            or len(asset["sha256"]) != 64
            or any(
                character not in "0123456789abcdef"
                for character in asset["sha256"].lower()
            )
            or not isinstance(asset.get("size_bytes"), int)
            or asset["size_bytes"] <= 0
        ):
            raise ModelSetupError("model_manifest_invalid", "Official model manifest is invalid.")
    if (
        sum(asset["size_bytes"] for asset in assets) != payload["size_bytes"]
        or _official_assets_identity(assets) != payload["sha256"]
    ):
        raise ModelSetupError("model_manifest_invalid", "Official model manifest is invalid.")
    return payload


def load_pytorch_runtime_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelSetupError(
            "pytorch_runtime_manifest_invalid",
            "PyTorch runtime manifest is invalid.",
        ) from exc
    if not isinstance(payload, dict):
        raise ModelSetupError(
            "pytorch_runtime_manifest_invalid",
            "PyTorch runtime manifest is invalid.",
        )
    expected = {
        "schema": PYTORCH_RUNTIME_MANIFEST_SCHEMA,
        "bundle_id": PYTORCH_RUNTIME_BUNDLE_ID,
        "version": PYTORCH_RUNTIME_VERSION,
        "package": PYTORCH_RUNTIME_PACKAGE,
        "python_version": PYTORCH_RUNTIME_PYTHON_VERSION,
        "torch_version": PYTORCH_RUNTIME_TORCH_VERSION,
        "cuda_version": PYTORCH_RUNTIME_CUDA_VERSION,
        "wheel_filename": PYTORCH_RUNTIME_WHEEL_FILENAME,
        "fallback_allowed": False,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise ModelSetupError(
            "pytorch_runtime_manifest_invalid",
            "PyTorch runtime manifest is invalid.",
        )
    if (
        not isinstance(payload.get("url"), str)
        or not payload["url"].startswith(PYTORCH_RUNTIME_URL_PREFIX)
        or not isinstance(payload.get("sha256"), str)
        or len(payload["sha256"]) != 64
        or any(
            character not in "0123456789abcdef"
            for character in payload["sha256"].lower()
        )
        or not isinstance(payload.get("size_bytes"), int)
        or payload["size_bytes"] <= 0
    ):
        raise ModelSetupError(
            "pytorch_runtime_manifest_invalid",
            "PyTorch runtime manifest is invalid.",
        )
    return payload


def model_status(*, manifest: dict[str, Any], model_root: Path) -> dict[str, Any]:
    marker = _read_json(model_root / ".totalseg_model_ready.json")
    ready = bool(
        marker
        and marker.get("schema") == READY_SCHEMA
        and marker.get("bundle_id") == manifest["bundle_id"]
        and marker.get("version") == manifest["version"]
        and marker.get("sha256") == manifest["sha256"]
        and _validate_model_root(
            model_root,
            manifest["datasets"],
            manifest["legal_files"],
            raise_error=False,
        )
    )
    if ready:
        return {"status": "ready", "model_state": "ready"}
    if manifest["schema"] == OFFICIAL_ASSETS_MANIFEST_SCHEMA:
        return _official_assets_status(manifest, model_root)
    archive = _archive_path(model_root, manifest)
    partial = archive.with_name(archive.name + ".part")
    state = _read_json(partial.with_name(partial.name + ".json"))
    resumable = bool(partial.is_file() and partial.stat().st_size > 0 and state == _partial_state(manifest))
    return {
        "status": "resumable" if resumable else "not_installed",
        "model_state": "resumable" if resumable else "not_installed",
        "downloaded_bytes": partial.stat().st_size if resumable else 0,
    }


def install_model_bundle(
    *,
    manifest: dict[str, Any],
    model_root: Path,
    legal_root: Path | None = None,
    timeout_sec: int = 7200,
) -> dict[str, Any]:
    model_root = model_root.expanduser().resolve()
    if manifest["schema"] == OFFICIAL_ASSETS_MANIFEST_SCHEMA:
        return _install_official_assets(
            manifest=manifest,
            model_root=model_root,
            legal_root=legal_root,
            timeout_sec=timeout_sec,
        )
    status = model_status(manifest=manifest, model_root=model_root)
    if status["model_state"] == "ready":
        return _result(manifest, status="success", model_state="ready", downloaded=False, resumed=False)

    archive = _archive_path(model_root, manifest)
    staging = model_root.parent / f".totalseg-model-staging-{uuid4().hex}"
    archive.parent.mkdir(parents=True, exist_ok=True)
    try:
        download = _download_bundle(manifest, archive, timeout_sec=timeout_sec)
        _emit("extract", "running", "モデルを展開しています。")
        extracted_root = _extract_bundle(archive, staging, manifest["archive_root"])
        _validate_model_root(
            extracted_root,
            manifest["datasets"],
            manifest["legal_files"],
            raise_error=True,
        )
        _write_json(
            extracted_root / ".totalseg_model_ready.json",
            {
                "schema": READY_SCHEMA,
                "bundle_id": manifest["bundle_id"],
                "version": manifest["version"],
                "sha256": manifest["sha256"],
                "datasets": manifest["datasets"],
                "validated_at": datetime.now(UTC).isoformat(),
            },
        )
        _publish(extracted_root, model_root)
        try:
            archive.unlink(missing_ok=True)
        except OSError:
            pass
        _emit("complete", "success", "モデルの準備が完了しました。", percent=100)
        return _result(
            manifest,
            status="success",
            model_state="ready",
            downloaded=True,
            resumed=download["resumed"],
        )
    except ModelSetupError:
        raise
    except Exception as exc:
        raise ModelSetupError("model_prepare_failed", "モデルの準備を完了できませんでした。") from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def pytorch_runtime_status(
    *,
    manifest: dict[str, Any],
    runtime_root: Path,
) -> dict[str, Any]:
    marker = _read_json(runtime_root / ".pytorch_runtime_ready.json")
    ready = bool(
        marker
        and marker.get("schema") == PYTORCH_RUNTIME_READY_SCHEMA
        and marker.get("bundle_id") == manifest["bundle_id"]
        and marker.get("version") == manifest["version"]
        and marker.get("sha256") == manifest["sha256"]
        and _validate_pytorch_runtime_root(runtime_root, raise_error=False)
    )
    if ready:
        return {"status": "ready", "runtime_state": "ready"}
    archive = _pytorch_runtime_archive_path(runtime_root, manifest)
    partial = archive.with_name(archive.name + ".part")
    state = _read_json(partial.with_name(partial.name + ".json"))
    resumable = bool(
        partial.is_file()
        and 0 < partial.stat().st_size < manifest["size_bytes"]
        and state == _partial_state(manifest)
    )
    return {
        "status": "resumable" if resumable else "not_installed",
        "runtime_state": "resumable" if resumable else "not_installed",
        "downloaded_bytes": partial.stat().st_size if resumable else 0,
    }


def install_pytorch_runtime(
    *,
    manifest: dict[str, Any],
    runtime_root: Path,
    timeout_sec: int = 7200,
) -> dict[str, Any]:
    runtime_root = runtime_root.expanduser().resolve()
    status = pytorch_runtime_status(manifest=manifest, runtime_root=runtime_root)
    if status["runtime_state"] == "ready":
        return {
            "status": "success",
            "runtime_state": "ready",
            "downloaded": False,
            "resumed": False,
        }
    archive = _pytorch_runtime_archive_path(runtime_root, manifest)
    staging = runtime_root.parent / f".pytorch-runtime-staging-{uuid4().hex}"
    archive.parent.mkdir(parents=True, exist_ok=True)
    try:
        download = _download_pytorch_runtime(
            manifest=manifest,
            archive=archive,
            timeout_sec=timeout_sec,
        )
        _emit("runtime_install", "running", "Installing verified PyTorch CUDA runtime.")
        _install_pytorch_wheel(archive, staging)
        _validate_pytorch_runtime_root(staging, raise_error=True)
        _write_json(
            staging / ".pytorch_runtime_ready.json",
            {
                "schema": PYTORCH_RUNTIME_READY_SCHEMA,
                "bundle_id": manifest["bundle_id"],
                "version": manifest["version"],
                "sha256": manifest["sha256"],
                "installed_at": datetime.now(UTC).isoformat(),
            },
        )
        _publish(staging, runtime_root)
        archive.unlink(missing_ok=True)
        _emit("runtime_complete", "success", "PyTorch CUDA runtime is ready.", percent=100)
        return {
            "status": "success",
            "runtime_state": "ready",
            "downloaded": True,
            "resumed": download["resumed"],
        }
    except ModelSetupError:
        raise
    except Exception as exc:
        raise ModelSetupError(
            "pytorch_runtime_prepare_failed",
            "PyTorch CUDA runtime setup failed.",
        ) from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def _official_assets_status(
    manifest: dict[str, Any],
    model_root: Path,
) -> dict[str, Any]:
    downloaded = 0
    resumable = False
    for asset in manifest["assets"]:
        archive = _official_asset_archive_path(model_root, manifest, asset)
        partial = archive.with_name(archive.name + ".part")
        if archive.is_file() and archive.stat().st_size == asset["size_bytes"]:
            if _sha256(archive) == asset["sha256"]:
                downloaded += archive.stat().st_size
                resumable = True
                continue
        state = _read_json(partial.with_name(partial.name + ".json"))
        if (
            partial.is_file()
            and 0 < partial.stat().st_size < asset["size_bytes"]
            and state == _official_asset_partial_state(manifest, asset)
        ):
            downloaded += partial.stat().st_size
            resumable = True
    return {
        "status": "resumable" if resumable else "not_installed",
        "model_state": "resumable" if resumable else "not_installed",
        "downloaded_bytes": downloaded,
    }


def _install_official_assets(
    *,
    manifest: dict[str, Any],
    model_root: Path,
    legal_root: Path | None,
    timeout_sec: int,
) -> dict[str, Any]:
    status = model_status(manifest=manifest, model_root=model_root)
    if status["model_state"] == "ready":
        return _result(manifest, status="success", model_state="ready", downloaded=False, resumed=False)
    if legal_root is None:
        raise ModelSetupError(
            "model_legal_files_unavailable",
            "Required TotalSegmentator legal files are unavailable.",
        )
    staging = model_root.parent / f".totalseg-model-staging-{uuid4().hex}"
    downloaded = False
    resumed = False
    try:
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "nnunet" / "results").mkdir(parents=True, exist_ok=True)
        for asset in manifest["assets"]:
            archive = _official_asset_archive_path(model_root, manifest, asset)
            download = _download_official_asset(
                manifest=manifest,
                asset=asset,
                archive=archive,
                timeout_sec=timeout_sec,
            )
            downloaded = True
            resumed = resumed or download["resumed"]
            _emit("extract", "running", "Extracting verified official model files.")
            extracted = _extract_bundle(archive, staging, asset["archive_root"])
            extracted.replace(
                staging / "nnunet" / "results" / asset["dataset"]
            )
        _write_json(staging / "config.json", {"send_usage_stats": False})
        _copy_legal_files(legal_root, staging / "legal", manifest["legal_files"])
        _validate_model_root(
            staging,
            manifest["datasets"],
            manifest["legal_files"],
            raise_error=True,
        )
        _write_json(
            staging / ".totalseg_model_ready.json",
            {
                "schema": READY_SCHEMA,
                "bundle_id": manifest["bundle_id"],
                "version": manifest["version"],
                "sha256": manifest["sha256"],
                "datasets": manifest["datasets"],
                "validated_at": datetime.now(UTC).isoformat(),
            },
        )
        _publish(staging, model_root)
        for asset in manifest["assets"]:
            _official_asset_archive_path(model_root, manifest, asset).unlink(
                missing_ok=True
            )
        _emit("complete", "success", "Official TotalSegmentator models are ready.", percent=100)
        return _result(
            manifest,
            status="success",
            model_state="ready",
            downloaded=downloaded,
            resumed=resumed,
        )
    except ModelSetupError:
        raise
    except Exception as exc:
        raise ModelSetupError(
            "model_prepare_failed",
            "Official TotalSegmentator model setup failed.",
        ) from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def _download_official_asset(
    *,
    manifest: dict[str, Any],
    asset: dict[str, Any],
    archive: Path,
    timeout_sec: int,
) -> dict[str, bool]:
    if archive.is_file() and archive.stat().st_size == asset["size_bytes"]:
        if _sha256(archive) == asset["sha256"]:
            return {"resumed": True}
        archive.unlink(missing_ok=True)
    source = {
        "bundle_id": manifest["bundle_id"],
        "version": f"{manifest['version']}-{asset['dataset']}",
        "url": asset["url"],
        "sha256": asset["sha256"],
        "size_bytes": asset["size_bytes"],
    }
    return _download_bundle(source, archive, timeout_sec=timeout_sec)


def _download_pytorch_runtime(
    *,
    manifest: dict[str, Any],
    archive: Path,
    timeout_sec: int,
) -> dict[str, bool]:
    if archive.is_file() and archive.stat().st_size == manifest["size_bytes"]:
        if _sha256(archive) == manifest["sha256"]:
            return {"resumed": True}
        archive.unlink(missing_ok=True)
    return _download_bundle(manifest, archive, timeout_sec=timeout_sec)


def _download_bundle(
    manifest: dict[str, Any],
    archive: Path,
    *,
    timeout_sec: int,
    allow_restart: bool = True,
) -> dict[str, bool]:
    partial = archive.with_name(archive.name + ".part")
    metadata = partial.with_name(partial.name + ".json")
    expected_state = _partial_state(manifest)
    state = _read_json(metadata)
    can_resume = bool(partial.is_file() and 0 < partial.stat().st_size < manifest["size_bytes"] and state == expected_state)
    if partial.is_file() and partial.stat().st_size == manifest["size_bytes"] and state == expected_state:
        if _sha256(partial) == manifest["sha256"]:
            partial.replace(archive)
            metadata.unlink(missing_ok=True)
            return {"resumed": True}
    if not can_resume:
        partial.unlink(missing_ok=True)
        metadata.unlink(missing_ok=True)
    _write_json(metadata, expected_state)
    offset = partial.stat().st_size if can_resume else 0
    digest = hashlib.sha256()
    if can_resume:
        with partial.open("rb") as existing:
            for chunk in iter(lambda: existing.read(CHUNK_SIZE), b""):
                digest.update(chunk)
    request: str | urllib.request.Request = manifest["url"]
    if can_resume:
        request = urllib.request.Request(manifest["url"], headers={"Range": f"bytes={offset}-"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:  # noqa: S310
            if can_resume and not _valid_range_response(response, offset):
                if not allow_restart:
                    raise ModelSetupError("model_download_failed", "モデルのダウンロードを再開できませんでした。")
                partial.unlink(missing_ok=True)
                metadata.unlink(missing_ok=True)
                return _download_bundle(manifest, archive, timeout_sec=timeout_sec, allow_restart=False)
            downloaded = offset
            started = time.perf_counter()
            _emit_download(downloaded, manifest["size_bytes"], resumed=can_resume, started=started, offset=offset)
            with partial.open("ab" if can_resume else "wb") as output:
                while chunk := response.read(CHUNK_SIZE):
                    output.write(chunk)
                    output.flush()
                    digest.update(chunk)
                    downloaded += len(chunk)
                    _emit_download(downloaded, manifest["size_bytes"], resumed=can_resume, started=started, offset=offset)
    except ModelSetupError:
        raise
    except Exception as exc:
        raise ModelSetupError("model_download_interrupted", "モデルのダウンロードが中断されました。再試行すると続きから再開します。") from exc
    if downloaded != manifest["size_bytes"]:
        raise ModelSetupError("model_download_interrupted", "モデルのダウンロードが中断されました。再試行すると続きから再開します。")
    if digest.hexdigest() != manifest["sha256"]:
        raise ModelSetupError("model_hash_mismatch", "ダウンロードしたモデルを検証できませんでした。")
    partial.replace(archive)
    metadata.unlink(missing_ok=True)
    return {"resumed": can_resume}


def _extract_bundle(archive_path: Path, staging: Path, archive_root: str) -> Path:
    wanted_root = PurePosixPath(archive_root)
    if wanted_root.is_absolute() or ".." in wanted_root.parts:
        raise ModelSetupError("model_archive_invalid", "モデルbundleの内容を確認できませんでした。")
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ModelSetupError("model_archive_invalid", "モデルbundleの内容を確認できませんでした。")
            if path.parts and path.parts[0] != wanted_root.parts[0]:
                raise ModelSetupError("model_archive_invalid", "モデルbundleの内容を確認できませんでした。")
        archive.extractall(staging)
    extracted = staging.joinpath(*wanted_root.parts)
    if not extracted.is_dir():
        raise ModelSetupError("model_archive_invalid", "モデルbundleの内容を確認できませんでした。")
    return extracted


def _validate_model_root(
    model_root: Path,
    datasets: list[str],
    legal_files: list[str],
    *,
    raise_error: bool,
) -> bool:
    try:
        config = json.loads((model_root / "config.json").read_text(encoding="utf-8"))
        if config.get("send_usage_stats") is not False:
            raise ValueError
        for dataset in datasets:
            root = model_root / "nnunet" / "results" / dataset
            if not root.is_dir() or not any(path.stat().st_size > 0 for path in root.rglob("checkpoint_final.pth")):
                raise ValueError
        for filename in legal_files:
            path = model_root / "legal" / filename
            if not path.is_file() or path.stat().st_size <= 0:
                raise ValueError
        return True
    except (OSError, ValueError, json.JSONDecodeError):
        if raise_error:
            raise ModelSetupError("model_content_invalid", "モデルbundleに必要なファイルがありません。")
        return False


def _install_pytorch_wheel(archive: Path, staging: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            "--no-index",
            "--target",
            str(staging),
            str(archive),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=1200,
    )
    if completed.returncode != 0:
        raise ModelSetupError(
            "pytorch_runtime_install_failed",
            "PyTorch CUDA runtime could not be installed.",
        )


def _validate_pytorch_runtime_root(
    runtime_root: Path,
    *,
    raise_error: bool,
) -> bool:
    try:
        if not (runtime_root / "torch" / "__init__.py").is_file():
            raise ValueError
        environment = os.environ.copy()
        existing_path = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = os.pathsep.join(
            value for value in (str(runtime_root), existing_path) if value
        )
        environment["PYTHONNOUSERSITE"] = "1"
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json, torch; print(json.dumps({"
                    "'torch_version': torch.__version__, "
                    "'cuda_version': torch.version.cuda}))"
                ),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            env=environment,
        )
        payload = json.loads(probe.stdout.strip())
        if (
            probe.returncode != 0
            or payload.get("torch_version") != PYTORCH_RUNTIME_TORCH_VERSION
            or payload.get("cuda_version") != PYTORCH_RUNTIME_CUDA_VERSION
        ):
            raise ValueError
        return True
    except (
        OSError,
        subprocess.SubprocessError,
        ValueError,
        json.JSONDecodeError,
    ):
        if raise_error:
            raise ModelSetupError(
                "pytorch_runtime_content_invalid",
                "PyTorch CUDA runtime verification failed.",
            ) from None
        return False


def _publish(staged: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(destination.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup)
    replaced = False
    try:
        if destination.exists():
            destination.replace(backup)
            replaced = True
        staged.replace(destination)
    except Exception:
        if replaced and backup.exists() and not destination.exists():
            backup.replace(destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def _archive_path(model_root: Path, manifest: dict[str, Any]) -> Path:
    return model_root.parent / "downloads" / f"{manifest['bundle_id']}-{manifest['version']}.zip"


def _pytorch_runtime_archive_path(
    runtime_root: Path,
    manifest: dict[str, Any],
) -> Path:
    return (
        runtime_root.parent
        / "downloads"
        / manifest["wheel_filename"]
    )


def _official_asset_archive_path(
    model_root: Path,
    manifest: dict[str, Any],
    asset: dict[str, Any],
) -> Path:
    return (
        model_root.parent
        / "downloads"
        / f"{manifest['bundle_id']}-{manifest['version']}-{asset['dataset']}.zip"
    )


def _official_asset_partial_state(
    manifest: dict[str, Any],
    asset: dict[str, Any],
) -> dict[str, Any]:
    return _partial_state(
        {
            "bundle_id": manifest["bundle_id"],
            "version": f"{manifest['version']}-{asset['dataset']}",
            "url": asset["url"],
            "sha256": asset["sha256"],
            "size_bytes": asset["size_bytes"],
        }
    )


def _official_assets_identity(assets: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        "".join(asset["sha256"] for asset in assets).encode("ascii")
    ).hexdigest()


def _copy_legal_files(
    source_root: Path,
    destination_root: Path,
    filenames: list[str],
) -> None:
    try:
        destination_root.mkdir(parents=True, exist_ok=True)
        for filename in filenames:
            source = source_root / filename
            if not source.is_file():
                source = source_root / "licenses" / filename
            if not source.is_file() or source.stat().st_size <= 0:
                raise ValueError
            shutil.copyfile(source, destination_root / filename)
    except (OSError, ValueError) as exc:
        raise ModelSetupError(
            "model_legal_files_unavailable",
            "Required TotalSegmentator legal files are unavailable.",
        ) from exc


def _partial_state(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "bundle_id": manifest["bundle_id"],
        "version": manifest["version"],
        "url_sha256": hashlib.sha256(manifest["url"].encode("utf-8")).hexdigest(),
        "sha256": manifest["sha256"],
        "size_bytes": manifest["size_bytes"],
    }


def _valid_range_response(response: Any, offset: int) -> bool:
    status = getattr(response, "status", None) or response.getcode()
    content_range = response.headers.get("Content-Range") if response.headers else None
    return status == 206 and isinstance(content_range, str) and content_range.startswith(f"bytes {offset}-")


def _emit_download(downloaded: int, total: int, *, resumed: bool, started: float, offset: int) -> None:
    elapsed = max(time.perf_counter() - started, 1e-6)
    rate = (downloaded - offset) / elapsed
    eta = max(0.0, (total - downloaded) / rate) if rate > 0 else None
    _emit(
        "download",
        "running",
        "モデルをダウンロードしています。",
        downloaded_bytes=downloaded,
        total_bytes=total,
        percent=max(0, min(100, round(downloaded * 100 / total))),
        rate_bps=rate if downloaded > offset else None,
        eta_seconds=eta,
        resumed=resumed,
    )


def _emit(stage: str, status: str, message: str, **values: Any) -> None:
    print(PROGRESS_PREFIX + json.dumps({"stage": stage, "status": status, "message": message, **values}, ensure_ascii=False, sort_keys=True), flush=True)


def _result(manifest: dict[str, Any], **values: Any) -> dict[str, Any]:
    return {
        "schema": SETUP_SCHEMA,
        "bundle_id": manifest["bundle_id"],
        "version": manifest["version"],
        "sha256_verified": values.get("model_state") == "ready",
        "fallback_allowed": False,
        **values,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--model-root", required=True, type=Path)
    parser.add_argument("--legal-root", type=Path)
    parser.add_argument("--pytorch-runtime-manifest", type=Path)
    parser.add_argument("--pytorch-runtime-root", type=Path)
    args = parser.parse_args()
    try:
        if (args.pytorch_runtime_manifest is None) != (
            args.pytorch_runtime_root is None
        ):
            raise ModelSetupError(
                "pytorch_runtime_arguments_invalid",
                "PyTorch CUDA runtime setup arguments are invalid.",
            )
        if args.pytorch_runtime_manifest is not None:
            install_pytorch_runtime(
                manifest=load_pytorch_runtime_manifest(
                    args.pytorch_runtime_manifest
                ),
                runtime_root=args.pytorch_runtime_root,
            )
        result = install_model_bundle(
            manifest=load_model_manifest(args.manifest),
            model_root=args.model_root,
            legal_root=args.legal_root,
        )
    except ModelSetupError as exc:
        print(json.dumps({"schema": SETUP_SCHEMA, "status": "failed", "error_code": exc.error_code, "safe_reason": exc.safe_reason, "fallback_allowed": False}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
