# Windows限定アルファ版のインストール

この配布物は、招待されたアルファテスター向けの自己署名MSIXです。
Microsoft Store版や一般公開版ではありません。

## 対象

- Windows 10/11 x64
- NVIDIA CUDA対応GPU
- 検証済み基準機: GeForce RTX 2060、driver 572.83
- 研究・教育・検証目的のみ

Windows 11での実アプリ検証、clean-machine検証、Store署名、更新・rollbackは
まだ完了していません。

## インストール

PowerShellを「管理者として実行」し、配布フォルダーへ移動して次を実行します。

```powershell
.\install_alpha_msix.ps1
```

スクリプトは次の処理を行います。

1. MSIX署名と同梱公開証明書のthumbprintを照合
2. 自己署名公開証明書を`LocalMachine\TrustedPeople`へ登録
3. 署名を再検証
4. 現在のユーザーへMSIXをインストール

秘密鍵やPFXは配布物に含まれません。証明書警告を無視してMSIXを直接開かず、
必ず同梱スクリプトを使ってください。

`LocalMachine\TrustedPeople`への登録は、このアルファ署名をPC全体で信頼する
管理者権限のセキュリティ変更です。招待元から受け取った配布物だけを使い、
`SHA256SUMS.txt`を確認してください。評価終了後は、下記の
`-RemoveTrustedCertificate`付きアンインストールで証明書も削除してください。

インストール後、スタートメニューから
「TotalSegmentator Wrapper for Windows Alpha」を起動します。

## このアルファ版の範囲

- strict `cuda:0`
- TotalSegmentator `craniofacial_structures`
- bundled NIfTI Sample 1
- Job Objectによる正常終了・停止
- DICOM clean intakeとSecondary Capture rescue

DentalSegmentator、Individual Teeth、ToothSegの追加モデルcheckpointは、
この最初のアルファMSIXには含まれません。該当ボタンは準備不足のtyped errorで
停止し、CPU fallbackやネットワーク取得は行いません。

## アンインストール

`uninstall_alpha_msix.ps1`をPowerShellで実行してください。結果フォルダーは
削除されません。自己署名証明書も削除する場合は次を実行します。

```powershell
.\uninstall_alpha_msix.ps1 -RemoveTrustedCertificate
```

証明書も削除する場合は、PowerShellを管理者として実行してください。

将来のMicrosoft Store版はPublisher identityが異なるため、この自己署名版を
先にアンインストールしてから導入してください。

## フィードバック

患者データ、DICOM、CT、mask、絶対パス、ユーザー名、raw third-party outputを
Issueやメールへ添付しないでください。非PHIのtyped error code、Windows build、
GPU名、driver versionだけを報告してください。
