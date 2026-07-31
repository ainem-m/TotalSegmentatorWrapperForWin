# Windows限定アルファ版（ポータブルZIP）

この配布物は、招待されたアルファテスター向けの非臨床アルファ版です。
Microsoft Store版や一般公開版ではありません。患者の診断、治療方針、
医療判断には使用しないでください。

ポータブルZIP版を、限定アルファ配布の推奨経路とします。管理者権限、
PowerShell、証明書登録、インストールは不要です。

## 起動

1. ZIPファイルを右クリックし、「すべて展開」を選びます。
2. 十分な空き容量があるローカルフォルダーへ展開します。
3. 展開先の`TSW`フォルダーを開きます。
4. `START_HERE_TotalSegmentatorWrapperForWin.exe`をダブルクリックします。

`tswm-process-supervisor.exe`は画面を持たない内部部品です。起動用EXEでは
ありません。portable ZIPでは取り違えを避けるため、ルートには置きません。

ZIP内のEXEを直接ダブルクリックしないでください。直接起動を検出した場合、
アプリは処理を始めず「すべて展開」の案内を表示します。

配布ZIPと内部フォルダーは、Windows Explorerのパス長制限を避ける短い名前に
してあります。古い`TotalSegmentatorWrapperForWin-Alpha-Portable_*.zip`は
使用しないでください。

Windows SmartScreenが表示される可能性がありますが、表示されない環境も
あります。警告の有無だけで成功・失敗を判断しないでください。招待元と
`SHA256SUMS.txt`のハッシュを確認できた場合だけ、「詳細情報」から実行して
ください。確認できないファイルは実行しないでください。

展開後は約5.6 GiBを使用します。実行結果、一時ファイル、設定は
ユーザーが書き込めるLocalAppData配下または画面で選択した保存先へ作成され、
展開した配布フォルダーへは保存しません。

## 動作範囲

- Windows 10/11 x64
- NVIDIA CUDA対応GPU
- strict `cuda:0`
- TotalSegmentator `craniofacial_structures`
- bundled NIfTI Sample 1
- Job Objectによる正常終了・停止
- DICOM clean intakeとSecondary Capture rescue
- ローカルassetだけを使うoffline preview

DentalSegmentator、Individual Teeth、ToothSegの追加モデルcheckpointは、
この最初のポータブルZIPには含まれません。該当機能は準備不足のtyped errorで
停止し、CPU fallbackやネットワーク取得は行いません。

## 検証状況

Windows 10の既存engineering hostでは、展開payloadのWPF、Job Object、
app-private Python/CUDA runtime、strict CUDA、bundled Sample 1、
offline preview、DICOM binariesを検証します。

Windows 11、GPU/driver構成の異なるclean machine、SmartScreenの表示差、
外部UI Automation、update/rollbackは未検証です。

## 終了と削除

実行中の処理を終了してアプリを閉じた後、展開したフォルダーとZIPを削除します。
過去の結果は自動削除されません。不要な結果は、画面で選択した保存先または
LocalAppData配下の`TotalSegmentatorWrapperWindows`から個別に削除してください。

## フィードバック

患者データ、DICOM、CT、mask、絶対パス、ユーザー名、raw third-party outputを
Issueやメールへ添付しないでください。非PHIのtyped error code、Windows build、
GPU名、driver versionだけを報告してください。
