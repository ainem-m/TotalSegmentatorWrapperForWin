from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsAlphaPortableContractTests(unittest.TestCase):
    def test_portable_build_is_offline_and_reuses_pinned_closure(self) -> None:
        script = (ROOT / "scripts" / "build_alpha_portable.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("<clear />", script)
        self.assertIn("DotNetPackageSource", script)
        self.assertIn("10.0.10.nupkg", script)
        self.assertIn("--no-index", script)
        self.assertIn("--no-deps", script)
        self.assertIn("Dataset115_mandible", script)
        self.assertIn(
            "Dataset297_TotalSegmentator_total_3mm_1559subj",
            script,
        )
        self.assertIn("Compression.ZipFile", script)
        self.assertIn('$portableDirectoryName = "TSW"', script)
        self.assertIn(
            '$portableEntrypoint = '
            '"START_HERE_TotalSegmentatorWrapperForWin.exe"',
            script,
        )
        self.assertIn(
            'Join-Path $portableRoot "createdump.exe"',
            script,
        )
        self.assertIn(
            '$maximumInternalPathCharacters = 180',
            script,
        )
        self.assertIn('"TSW-Alpha-{0}-win-x64.zip"', script)
        self.assertNotIn("Invoke-WebRequest", script)
        self.assertNotIn("Add-AppxPackage", script)
        self.assertNotIn("Import-Certificate", script)

    def test_portable_payload_has_self_diagnostics_and_no_distribution_writes(
        self,
    ) -> None:
        build = (ROOT / "scripts" / "build_alpha_portable.ps1").read_text(
            encoding="utf-8"
        )
        session = (
            ROOT
            / "native"
            / "windows"
            / "CoordinatorShell"
            / "CoordinatorSession.cs"
        ).read_text(encoding="utf-8")
        configuration = (
            ROOT
            / "native"
            / "windows"
            / "CoordinatorShell"
            / "ShellConfiguration.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("--portable-self-test", build)
        self.assertIn("write_portable_runtime_diagnostic.py", build)
        self.assertIn("PYTHONDONTWRITEBYTECODE", session)
        self.assertIn("TOTALSEG_WEIGHTS_PATH", session)
        self.assertIn('"totalseg-state"', session)
        self.assertIn(
            '["-m", "totalsegmentator_wrapper_mac.coordinator"]',
            configuration,
        )
        self.assertNotIn(
            '"Scripts",\n                    "totalsegmentator-wrapper-coordinator.exe"',
            configuration,
        )
        self.assertIn("SpecialFolder.LocalApplicationData", configuration)
        self.assertIn(
            '"runtime", "native"',
            configuration,
        )
        self.assertIn(
            'distribution_directory_writable = $false',
            build,
        )
        self.assertIn(
            'results_location = "user_selected_or_local_app_data"',
            build,
        )

    def test_zip_direct_launch_guard_is_visible_and_contract_tested(self) -> None:
        app = (
            ROOT
            / "native"
            / "windows"
            / "CoordinatorShell"
            / "App.xaml.cs"
        ).read_text(encoding="utf-8")
        guard = (
            ROOT
            / "native"
            / "windows"
            / "CoordinatorShell"
            / "PortableLaunchGuard.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("ZIP内から直接起動できません", app)
        self.assertIn("すべて展開", app)
        self.assertIn("portable_archive_guard", app)
        self.assertIn('StartsWith(\n                            "Temp"', guard)
        self.assertIn('Contains(\n                            ".zip"', guard)
        self.assertIn("ContractSelfTest", guard)

    def test_manual_makes_portable_the_low_friction_alpha_path(self) -> None:
        manual = (ROOT / "docs" / "README_PORTABLE_JA.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("推奨経路", manual)
        self.assertIn("管理者権限", manual)
        self.assertIn("PowerShell", manual)
        self.assertIn("証明書登録", manual)
        self.assertIn("インストールは不要", manual)
        self.assertIn("すべて展開", manual)
        self.assertIn("Windows Explorerのパス長制限", manual)
        self.assertIn(
            "START_HERE_TotalSegmentatorWrapperForWin.exe",
            manual,
        )
        self.assertIn("起動用EXEでは", manual)
        self.assertIn("表示されない環境", manual)
        self.assertIn("SmartScreen", manual)
        self.assertIn("約5.6 GiB", manual)
        self.assertIn("非臨床", manual)
        self.assertIn("Windows 11", manual)
        self.assertIn("clean machine", manual)
        self.assertIn("展開した配布フォルダーへは保存しません", manual)

    def test_msix_implementation_remains_available(self) -> None:
        self.assertTrue((ROOT / "scripts" / "build_alpha_msix.ps1").is_file())
        self.assertTrue((ROOT / "scripts" / "install_alpha_msix.ps1").is_file())
        self.assertTrue((ROOT / "docs" / "ALPHA_INSTALL_JA.md").is_file())


if __name__ == "__main__":
    unittest.main()
