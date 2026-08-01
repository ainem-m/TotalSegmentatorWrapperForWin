# 軽量ポータブル ZIP（後工程メモ）

現在の完全オフライン版ポータブル ZIP は残し、後工程で軽量な
bootstrap ZIP を追加する。

## 方針

- 初期 ZIP には WPF shell、Job Object supervisor、DICOM binaries、
  bundled sample、app-private Python/CUDA/PyTorch runtime、取得・検証機能を含める。
- TotalSegmentatorモデル checkpointだけを、初回起動後にアプリ内から取得する。
- public package index で依存解決せず、社内配布元に置いた検証済みbundleを使う。
- bundleはexact versionとSHA-256を記録したmanifestで固定する。
- ダウンロードは中断再開、hash検証、部分artifactの安全な扱いに対応する。
- モデルとpartial artifactはユーザー書込み可能領域へ保存し、ZIP展開フォルダーへ書かない。
- 展開後にproduction imports、モデル、strict CUDAの自己診断を行う。
- NVIDIA driverは取得・同梱せず、互換性を診断して不足時は案内する。
- strict CUDAが成立しない場合はtyped failureとし、CPUへfallbackしない。

## 配布形態

- 完全オフライン ZIP: 容量は大きいが、追加取得なしで実行できる。
- 軽量bootstrap ZIP: 初回取得が必要だが、最初の配布容量を小さくできる。

軽量版を追加しても、完全オフライン版を削除または置換しない。

## 未決事項

- 社内bundleの配布先とアクセス方式
- manifestの署名または真正性確認方式
- model bundleの更新ポリシー
- 初回取得に必要な空き容量表示と失敗時の再開UX
- clean-machineおよびWindows 11での検証
