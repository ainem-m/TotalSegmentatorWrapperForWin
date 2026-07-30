from __future__ import annotations

import unittest
from pathlib import Path

from totalsegmentator_wrapper_mac.disclaimers import NON_CLINICAL_NOTICE_EN


ROOT = Path(__file__).resolve().parents[1]


class NonClinicalLanguageTests(unittest.TestCase):
    def test_public_readme_states_non_clinical_boundary(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for required in (
            "研究・教育・検証用",
            "医療機器ではなく",
            "診断",
            "治療計画",
            "臨床利用には使用できません",
        ):
            with self.subTest(required=required):
                self.assertIn(required, readme)

    def test_wpf_shell_keeps_visible_non_clinical_copy(self) -> None:
        xaml = (
            ROOT
            / "native"
            / "windows"
            / "CoordinatorShell"
            / "MainWindow.xaml"
        ).read_text(encoding="utf-8")

        self.assertIn("研究・教育目的の非臨床プレビューです。", xaml)
        self.assertIn("医療機器ではなく", xaml)
        self.assertIn("臨床利用には使用できません。", xaml)

    def test_generated_reports_use_shared_english_notice(self) -> None:
        self.assertIn("not a medical device", NON_CLINICAL_NOTICE_EN)
        for relative in (
            "src/totalsegmentator_wrapper_mac/case_summary.py",
            "src/totalsegmentator_wrapper_mac/output_report.py",
        ):
            with self.subTest(relative=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn(
                    "from totalsegmentator_wrapper_mac.disclaimers "
                    "import NON_CLINICAL_NOTICE_EN",
                    source,
                )


if __name__ == "__main__":
    unittest.main()
