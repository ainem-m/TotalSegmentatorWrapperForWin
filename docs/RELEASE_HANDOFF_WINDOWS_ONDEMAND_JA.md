# Windows オンデマンド版: 公開ページ引継ぎメモ

## 対象ビルド

- ファイル名: `TSW-Alpha-0.4.0.0-ondemand-win-x64.zip`
- 配布 ZIP サイズ: 466,326,227 bytes（約 466 MB）
- SHA-256: `9fcf1719c6db0f3e9d87fc79a7be31630d34324ae0336c5d9109525ebda0c644`
- 形式: 展開して `START_HERE_TotalSegmentatorWrapperForWin.exe` を実行する Windows x64 portable 版

この ZIP は 1 GB 未満にするため、PyTorch/CUDA 本体と TotalSegmentator の
モデル重みを同梱しないオンデマンド版です。`site-packages\\torch` と
`torch-*.dist-info` は配布物に含めません。

## 初回準備の説明（公開ページ向け）

初回の「モデルを取得して準備」で、次をユーザーの LocalAppData に取得します。

- PyTorch CUDA 12.6: `torch 2.11.0+cu126`（Python 3.12 / Windows x64）
- TotalSegmentator 公式モデル: `Dataset115_mandible` と
  `Dataset297_TotalSegmentator_total_3mm_1559subj`

PyTorch は `download.pytorch.org`、モデルは TotalSegmentator 公式 GitHub
Releases から取得します。どちらも固定 manifest の SHA-256 とサイズを照合し、
中断時は `.part` を残して HTTP Range で再開します。準備中は数 GB の通信量と
空き容量が必要です。配布 ZIP が小さいことと、初回準備が小さいことは別です。

モデル・PyTorch は次のユーザー領域に保存され、展開した ZIP フォルダへ書き込みません。

```text
%LocalAppData%\\TotalSegmentatorWrapperWindows\\models\\totalseg-home
%LocalAppData%\\TotalSegmentatorWrapperWindows\\runtime\\python-site-packages
```

## 掲載文案

> **軽量オンデマンド版（約466 MB）**
> 初回だけ、GPU 実行環境（PyTorch/CUDA）と必要な TotalSegmentator 公式モデルを
> ダウンロードして検証します。以後は同じユーザー領域を再利用します。初回は数 GB の
> 通信量・空き容量が必要です。NVIDIA GPU（CUDA）が必要です。

## Windows での検証結果

- portable self-test（導入前）: pass、オンデマンド準備可能
- PyTorch 導入後: `torch 2.11.0+cu126` / CUDA `12.6` /
  `torch.cuda.is_available() = true`
- `Chino keisuke` DICOM の TotalSegmentator E2E: pass
  - `cuda:0` を解決
  - CPU フォールバックなし
  - 3方向 MPR プレビューとオフラインプレビューを生成

## Mac 側の取得

```bash
git fetch origin
git switch --track origin/agent/alpha-portable-zip
```

Release asset は Git には含めず、GitHub Release に添付します。公開ページでは
Release asset のダウンロード URL、上記 SHA-256、初回準備の説明を掲載してください。
