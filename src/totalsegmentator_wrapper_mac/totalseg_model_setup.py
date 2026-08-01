from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4


MANIFEST_SCHEMA = "totalsegmentator_wrapper.windows_totalseg_model_bundle.v1"
READY_SCHEMA = "totalsegmentator_wrapper.windows_totalseg_model_ready.v1"
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
    timeout_sec: int = 7200,
) -> dict[str, Any]:
    model_root = model_root.expanduser().resolve()
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
    args = parser.parse_args()
    try:
        result = install_model_bundle(
            manifest=load_model_manifest(args.manifest),
            model_root=args.model_root,
        )
    except ModelSetupError as exc:
        print(json.dumps({"schema": SETUP_SCHEMA, "status": "failed", "error_code": exc.error_code, "safe_reason": exc.safe_reason, "fallback_allowed": False}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
