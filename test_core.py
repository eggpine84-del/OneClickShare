"""
Core 순수 함수 로직 단위 테스트 모듈
"""
import unittest
from core.checker import (
    is_valid_share_name,
    build_unc_path,
    is_same_subnet,
    generate_powershell_firewall_command,
    generate_powershell_service_command,
    parse_printer_list_output,
    generate_subnet_ip_list,
    is_printer_disabled,
    format_printer_label,
    extract_actual_printer_name
)


class TestCoreLogic(unittest.TestCase):
    def test_is_valid_share_name(self):
        self.assertTrue(is_valid_share_name("CompanyShare"))
        self.assertTrue(is_valid_share_name("회사공용폴더"))
        self.assertFalse(is_valid_share_name(""))
        self.assertFalse(is_valid_share_name("Share/Folder"))
        self.assertFalse(is_valid_share_name('Share*Folder?'))

    def test_build_unc_path(self):
        self.assertEqual(build_unc_path("192.168.0.10", "Share"), r"\\192.168.0.10\Share")
        self.assertEqual(build_unc_path(r"\\DESKTOP-MAIN\\", r"/MyFolder/"), r"\\DESKTOP-MAIN\MyFolder")
        self.assertEqual(build_unc_path("", "Share"), "")

    def test_is_same_subnet(self):
        self.assertTrue(is_same_subnet("192.168.0.10", "192.168.0.25", "255.255.255.0"))
        self.assertFalse(is_same_subnet("192.168.0.10", "192.168.1.25", "255.255.255.0"))
        self.assertFalse(is_same_subnet("invalid_ip", "192.168.0.1"))

    def test_generate_powershell_commands(self):
        fw_cmd = generate_powershell_firewall_command("TestRule", "TCP", 445)
        self.assertIn("LocalPort 445", fw_cmd)
        self.assertIn("Protocol TCP", fw_cmd)

        svc_cmd = generate_powershell_service_command("FDResPub")
        self.assertIn('Set-Service -Name "FDResPub"', svc_cmd)

    def test_parse_printer_list_output(self):
        raw = "Canon MP250;;True\nHP LaserJet;;False\n"
        printers = parse_printer_list_output(raw)
        self.assertEqual(len(printers), 2)
        self.assertEqual(printers[0], ("Canon MP250", True))
        self.assertEqual(printers[1], ("HP LaserJet", False))

    def test_generate_subnet_ip_list(self):
        ips = generate_subnet_ip_list("192.168.0.15", "255.255.255.0")
        self.assertEqual(len(ips), 253)
        self.assertNotIn("192.168.0.15", ips)  # 자기 자신 제외 확인
        self.assertIn("192.168.0.1", ips)
        self.assertIn("192.168.0.254", ips)

    def test_is_printer_disabled(self):
        self.assertTrue(is_printer_disabled(None))
        self.assertTrue(is_printer_disabled(""))
        self.assertTrue(is_printer_disabled("   "))
        self.assertTrue(is_printer_disabled("(프린터 공유 안 함 - 폴더만 공유)"))
        self.assertTrue(is_printer_disabled("(프린터 연결 안 함 - 폴더만 연결)"))
        self.assertTrue(is_printer_disabled("(설치된 프린터가 없습니다)"))
        self.assertTrue(is_printer_disabled("[선택 안 함]"))
        self.assertFalse(is_printer_disabled("Samsung ML-1640 Series"))
        self.assertFalse(is_printer_disabled("Canon G3000 series"))

    def test_format_and_extract_printer_label(self):
        # 1. 라벨 생성 포맷 검증
        self.assertEqual(format_printer_label("Samsung ML-1640", True), "Samsung ML-1640 [공유 중]")
        self.assertEqual(format_printer_label("Canon G3000", False), "Canon G3000")
        self.assertEqual(format_printer_label("", True), "")

        # 2. 실제 프린터명 역추출 검증
        self.assertEqual(extract_actual_printer_name("Samsung ML-1640 [공유 중]"), "Samsung ML-1640")
        self.assertEqual(extract_actual_printer_name("Canon G3000"), "Canon G3000")
        self.assertEqual(extract_actual_printer_name("HP LaserJet [공유중]"), "HP LaserJet")
        self.assertEqual(extract_actual_printer_name("(프린터 공유 안 함 - 폴더만 공유)"), "(프린터 공유 안 함 - 폴더만 공유)")
        self.assertEqual(extract_actual_printer_name(None), "")


if __name__ == "__main__":
    unittest.main()

