# TotalSegmentator Wrapper for Windows

Windows上で、CTから顎骨・歯の非臨床3Dプレビューを作成するための
オープンソース実装です。WPF shell、.NET Job Object supervisor、
Python coordinator、DICOM normalizerを1つのリポジトリで管理します。

> 本ソフトウェアは研究・教育・検証用です。医療機器ではなく、診断、治療方針の
> 決定、治療計画、定量的な精度評価、または臨床利用には使用できません。

## 公開状態

このリポジトリは **engineering alpha / source release** です。

- Windows 10 x64実機でstrict NVIDIA CUDA、Job Object、WPF、bundled sample、
  DICOM/MSVC vertical sliceを検証済み
- Windows 11は未検証
- installer、署名、update/rollback、clean-machine導入は未実装・未検証
- 配布用Python runtime、wheelhouse、モデルcheckpointは同梱していません
- fake、mock、CPU fallbackを実CUDA成功として扱いません

現時点では一般利用者向け完成版ではありません。検証済み範囲は
[Windows verification matrix](docs/windows/02_WINDOWS_VERIFICATION_MATRIX.md) と
[`artifacts/spike/`](artifacts/spike/) を確認してください。

## 実装されている境界

- `native/windows/CoordinatorShell/` — package-free WPF shell
- `native/windows/ProcessSupervisor/` — suspended create、Job Object assign、resume、
  cancellationを担当するcoordinator専用supervisor
- `native/dicom_normalizer/` — GDCM/dcm2niixを使うnative DICOM intake
- `src/totalsegmentator_wrapper_mac/` — Python coordinatorと共通backend
- `resources/sample1/` — 非臨床bundled sampleとoffline preview

Python packageの内部namespaceには、既存protocol・evidence互換のため
`totalsegmentator_wrapper_mac` という旧名が残っています。Windowsの公開CLIは
`totalsegmentator-wrapper-coordinator` です。

## strict CUDA契約

Windows production coordinatorは `cuda_required(index)` のみを受け付けます。

- requested policyとresolved deviceを別々に記録
- `cuda:N`上でtensor/Conv3d/normalization/activation/ConvTranspose3dを検証
- CUDAが利用できない場合はtyped failure
- 同じoperation内でCPUへfallbackしない
- OOM時に解像度、ROI、class、モデルを黙って変更しない

検証済みWindows 10 engineering host:

- Python 3.12.10 x64
- PyTorch 2.11.0+cu126 / CUDA build 12.6
- TotalSegmentator 2.14.0
- NVIDIA GeForce RTX 2060 / driver 572.83

これは対応GPUの保証や最小要件ではありません。

## 開発

必要なSDK:

- Windows 10/11 x64
- .NET SDK 10.0.302
- Python 3.12
- CMakeとMSVC（DICOM normalizerをbuildする場合）

WPF shell:

```powershell
dotnet restore native/windows/CoordinatorShell/CoordinatorShell.csproj
dotnet build native/windows/CoordinatorShell/CoordinatorShell.csproj -c Release
dotnet build native/windows/ProcessSupervisor/ProcessSupervisor.csproj -c Release
```

Python tests:

```powershell
python -m pip install -e .
python -m unittest discover -s tests
```

app-private Windows runtimeはpublic indexからcustomer machine上で解決する設計では
ありません。検証済みbinary-only/hash-locked closureは
[`artifacts/spike/windows-runtime-cuda/requirements-win-x64-hashed.txt`](artifacts/spike/windows-runtime-cuda/requirements-win-x64-hashed.txt)
に記録されていますが、社内wheelhouse自体は公開していません。

## データとプライバシー

- patient dataをリポジトリ、Issue、Pull Requestへ追加しないでください
- DICOM、CT、生成mask、絶対パス、ユーザー名、raw third-party outputを公開しないでください
- Issueにはアプリが生成した非PHIのtyped errorだけを記載してください
- bundled/synthetic sampleだけを公開検証に使用します

## 第三者ソフトウェアとモデル

本プロジェクトはTotalSegmentatorの公式Windows版ではありません。
モデルcheckpointや第三者binaryは本リポジトリのApache-2.0で再ライセンスされません。
詳細は [NOTICE](NOTICE)、[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)、
[`resources/third_party/`](resources/third_party/) を参照してください。

## ライセンス

本プロジェクト独自のコードと文書は、個別の記載がない限り
[Apache License 2.0](LICENSE) で公開します。
