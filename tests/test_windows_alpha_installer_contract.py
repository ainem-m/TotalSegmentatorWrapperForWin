from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsAlphaInstallerContractTests(unittest.TestCase):
    def test_build_uses_fixed_alpha_identity_and_store_certificate(self) -> None:
        script = (ROOT / "scripts" / "build_alpha_msix.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn('TotalSegmentatorWrapperForWin.Alpha', script)
        self.assertIn('CN=TotalSegmentatorWrapperForWin Alpha', script)
        self.assertIn('Cert:\\CurrentUser\\My', script)
        self.assertIn('/fd SHA256', script)
        self.assertIn('/sha1 $thumbprint', script)
        self.assertNotIn('Export-PfxCertificate', script)

    def test_build_is_offline_for_python_and_fails_closed_on_models(self) -> None:
        script = (ROOT / "scripts" / "build_alpha_msix.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn('--no-index', script)
        self.assertIn('--no-deps', script)
        self.assertIn('Dataset115_mandible', script)
        self.assertIn(
            'Dataset297_TotalSegmentator_total_3mm_1559subj',
            script,
        )
        self.assertIn('send_usage_stats', script)
        self.assertIn('totalsegmentator_wrapper_mac-*.dist-info', script)
        self.assertIn('Legacy wrapper distribution metadata remains', script)
        self.assertIn('<clear />', script)
        self.assertIn('DotNetPackageSource', script)
        self.assertIn('10.0.10.nupkg', script)
        self.assertIn('pinned closure', script)
        self.assertIn('future\\backports\\test', script)
        self.assertIn('private-key-like file', script)
        self.assertIn('--no-restore', script)
        self.assertIn('-p:NuGetAudit=false', script)
        self.assertNotIn('Invoke-WebRequest', script)

    def test_installer_verifies_signature_before_install(self) -> None:
        script = (ROOT / "scripts" / "install_alpha_msix.ps1").read_text(
            encoding="utf-8"
        )
        verify_index = script.index('Get-AuthenticodeSignature')
        install_index = script.index('Add-AppxPackage')
        self.assertLess(verify_index, install_index)
        self.assertIn('Cert:\\LocalMachine\\TrustedPeople', script)
        self.assertIn('WindowsBuiltInRole]::Administrator', script)
        self.assertIn('TotalSegmentatorWrapperForWin.Alpha', script)

    def test_private_key_and_packages_are_not_tracked(self) -> None:
        tracked = [
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and ".git" not in path.parts
            and path.suffix.lower() in {".pfx", ".msix", ".msixbundle"}
        ]
        self.assertEqual([], tracked)

    def test_tester_manual_preserves_unverified_boundaries(self) -> None:
        manual = (ROOT / "docs" / "ALPHA_INSTALL_JA.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Windows 11", manual)
        self.assertIn("まだ完了していません", manual)
        self.assertIn("CPU fallback", manual)
        self.assertIn("秘密鍵やPFXは配布物に含まれません", manual)
        self.assertIn("LocalMachine\\TrustedPeople", manual)
        self.assertIn("管理者として実行", manual)
        self.assertIn("-RemoveTrustedCertificate", manual)
        self.assertIn("先にアンインストール", manual)


if __name__ == "__main__":
    unittest.main()
