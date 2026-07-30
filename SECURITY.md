# Security Policy

## Supported versions

現在はengineering alphaのため、`main`の最新commitのみを対象に確認します。
一般利用者向けbinary releaseはまだありません。

## Reporting a vulnerability

脆弱性やpatient-data exposureの可能性は公開Issueへ投稿せず、GitHubの
[Private vulnerability reporting](https://github.com/ainem-m/TotalSegmentatorWrapperForWin/security/advisories/new)
から報告してください。

報告には可能な範囲で次を含めてください。

- 影響を受けるcommit
- patient dataを含まない再現手順
- 想定される影響
- 回避策がある場合はその内容

DICOM、CT、生成結果、認証情報、個人情報、secret、不要な絶対パスは添付しないで
ください。

## Scope

Windows shell、coordinator、Job Object supervisor、DICOM normalizer、
dependency closure、artifact verificationに関するsecurity issueが対象です。
生成結果の医学的妥当性や診断相談は対象外です。
