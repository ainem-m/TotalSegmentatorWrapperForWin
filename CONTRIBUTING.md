# Contributing

TotalSegmentator Wrapper for Windowsへの関心をありがとうございます。

## 最初に確認すること

- 本ソフトウェアは研究・教育・検証用で、医療機器ではありません。
- patient name、ID、生年月日、施設名などの個人情報を含めないでください。
- DICOM、CT、mask、実行結果、raw third-party outputをIssueやPRへ添付しないでください。
- 大きな機能追加は、実装前にIssueで目的と範囲を相談してください。

## Bug report

Issue templateを使い、次を記録してください。

- source commitまたはversion
- Windows edition、version、build、x64
- GPU、driver、VRAM
- Python、PyTorch、CUDA build
- 再現手順
- typed error codeと非PHIのsafe message

patient dataや絶対パスを含むログは投稿しないでください。

## Pull Request

1. `main`の最新状態から作業branchを作ります。
2. 変更範囲を必要最小限にします。
3. bug fixには可能なら回帰テストを追加します。
4. 実行したchecksと結果、未検証項目をPRへ記載します。
5. UI変更ではbundled/synthetic sampleによる画像を使います。
6. 新しい依存やモデルにはlicense、provenance、binary availabilityを記録します。

基本checks:

```powershell
dotnet build native/windows/CoordinatorShell/CoordinatorShell.csproj -c Release
dotnet build native/windows/ProcessSupervisor/ProcessSupervisor.csproj -c Release
python -m unittest discover -s tests
git diff --check
```

実CUDA、DICOM/MSVC、署名、installerなどを実行できない場合は、成功扱いにせず
`UNVERIFIED`として明記してください。

## License

Pull Requestを送信することで、提出したfirst-party変更を本プロジェクトの
[Apache License 2.0](LICENSE) で提供することに同意したものとします。
