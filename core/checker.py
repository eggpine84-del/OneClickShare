"""
비즈니스 로직 및 순수 함수(Pure Function) 모듈
이 모듈은 네트워크/파일 I/O, 시간, 외부 상태에 의존하지 않고 오직 인풋 값만을 기반으로 결과를 계산합니다.
"""
import ipaddress
import re
from typing import List, Tuple, Optional


def is_valid_share_name(name: str) -> bool:
    """
    공유 폴더 또는 프린터 공유 이름이 윈도우 규칙에 유효한지 검증합니다.

    Args:
        name: 검증할 공유 이름 문자열

    Returns:
        유효하면 True, 그렇지 않으면 False
    """
    # Guard Clause: 빈 문자열 또는 공백 검사
    if not name or not name.strip():
        return False
    
    # 금지된 특수문자 검사: \ / : * ? " < > |
    invalid_chars_regex = r'[\\/:*?"<>|]'
    if re.search(invalid_chars_regex, name):
        return False
    
    # 윈도우 공유 이름 길이 제한 (통상 80자 이내 권장)
    if len(name) > 80:
        return False
        
    return True


def build_unc_path(host: str, share_name: str) -> str:
    """
    호스트명(또는 IP)과 공유 이름을 받아 표준 UNC 네트워크 경로를 생성합니다.

    Args:
        host: 호스트 이름 또는 IP 주소 (예: '192.168.0.10' 또는 'DESKTOP-MAIN')
        share_name: 공유 이름 (예: 'CompanyShare' 또는 'OfficePrinter')

    Returns:
        표준 UNC 경로 문자열 (예: r"\\192.168.0.10\CompanyShare")
    """
    # Guard Clause: 인풋 정제 (양끝의 슬래시 및 역슬래시 제거)
    clean_host = host.strip().strip("\\/")
    clean_share = share_name.strip().strip("\\/")
    
    if not clean_host or not clean_share:
        return ""
        
    return rf"\\{clean_host}\{clean_share}"


def is_same_subnet(ip1: str, ip2: str, subnet_mask: str = "255.255.255.0") -> bool:
    """
    두 IP 주소가 동일한 서브넷(로컬 네트워크) 대역에 속해 있는지 판별합니다.

    Args:
        ip1: 첫 번째 IP 주소 (예: '192.168.0.10')
        ip2: 두 번째 IP 주소 (예: '192.168.0.25')
        subnet_mask: 서브넷 마스크 (기본값: '255.255.255.0')

    Returns:
        동일 서브넷이면 True, 서로 다른 망이면 False
    """
    # Guard Clause: IPv4 형식 기본 검증
    try:
        net1 = ipaddress.IPv4Network(f"{ip1}/{subnet_mask}", strict=False)
        net2 = ipaddress.IPv4Network(f"{ip2}/{subnet_mask}", strict=False)
        return net1 == net2
    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError):
        return False


def generate_powershell_firewall_command(rule_name: str, protocol: str, port: int) -> str:
    """
    윈도우 방화벽 규칙을 추가하기 위한 순수 PowerShell 명령어 문자열을 생성합니다.

    Args:
        rule_name: 방화벽 규칙 명칭
        protocol: 프로토콜 (TCP 또는 UDP)
        port: 포트 번호

    Returns:
        PowerShell 실행 명령어 문자열
    """
    # Guard Clause
    upper_proto = protocol.upper()
    if upper_proto not in ("TCP", "UDP") or port <= 0 or port > 65535:
        return ""

    cmd = (
        f'New-NetFirewallRule -DisplayName "{rule_name}_{upper_proto}_{port}" '
        f'-Direction Inbound -LocalPort {port} -Protocol {upper_proto} '
        f'-Action Allow -Profile Any -ErrorAction SilentlyContinue'
    )
    return cmd


def generate_powershell_service_command(service_name: str) -> str:
    """
    윈도우 서비스를 '자동 시작'으로 설정하고 즉시 가동하는 순수 PowerShell 명령어 문자열을 생성합니다.

    Args:
        service_name: 서비스 영문 식별자

    Returns:
        PowerShell 실행 명령어 문자열
    """
    if not service_name or not service_name.strip():
        return ""
        
    clean_name = service_name.strip()
    return f'Set-Service -Name "{clean_name}" -StartupType Automatic -ErrorAction SilentlyContinue; Start-Service -Name "{clean_name}" -ErrorAction SilentlyContinue'


def parse_printer_list_output(raw_output: str) -> List[Tuple[str, bool]]:
    """
    PowerShell Get-Printer 출력 결과를 파싱하여 (프린터이름, 공유여부) 튜플 리스트로 변환합니다.

    Args:
        raw_output: PowerShell 출력 텍스트 (줄 단위 구분)

    Returns:
        [(프린터 이름, 공유 활성화 여부), ...] 리스트
    """
    result: List[Tuple[str, bool]] = []
    if not raw_output or not raw_output.strip():
        return result

    for line in raw_output.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("Name") or line.startswith("----"):
            continue
            
        parts = line.split(";;")
        if len(parts) >= 2:
            p_name = parts[0].strip()
            p_shared = parts[1].strip().lower() == "true"
            if p_name and p_name.lower() not in ("true", "false"):
                result.append((p_name, p_shared))
        elif len(parts) == 1 and parts[0].strip():
            fallback_name = parts[0].strip()
            if fallback_name.lower() not in ("true", "false"):
                result.append((fallback_name, False))
            
    return result


def generate_subnet_ip_list(local_ip: str, subnet_mask: str = "255.255.255.0") -> List[str]:
    """
    로컬 IP와 서브넷 마스크를 기반으로 스캔 대상이 되는 동일 서브넷의 모든 호스트 IP 목록을 생성합니다.

    Args:
        local_ip: 현재 컴퓨터의 로컬 IP (예: '192.168.0.15')
        subnet_mask: 서브넷 마스크 (기본값: '255.255.255.0')

    Returns:
        스캔 대상 IP 문자열 목록 (예: ['192.168.0.1', '192.168.0.2', ...])
    """
    ip_list: List[str] = []
    # Guard Clause: 루프백 및 잘못된 IP 필터링
    if not local_ip or local_ip == "127.0.0.1" or local_ip.startswith("169.254"):
        return ["127.0.0.1"]

    try:
        network = ipaddress.IPv4Network(f"{local_ip}/{subnet_mask}", strict=False)
        # 네트워크 및 브로드캐스트 주소를 제외한 모든 유효 호스트 추출
        for ip in network.hosts():
            ip_str = str(ip)
            if ip_str != local_ip:  # 자기 자신 제외
                ip_list.append(ip_str)
    except Exception:
        return ["127.0.0.1"]

    return ip_list


def filter_preferred_local_ip(ip_candidates: List[str]) -> str:
    """
    여러 네트워크 어댑터 IP 후보 중에서 최적의 사내망 로컬 IPv4 주소를 선별합니다.

    Args:
        ip_candidates: 검색된 IP 주소 문자열 목록

    Returns:
        가장 우선순위가 높은 사내망 IPv4 주소 (기본값: '127.0.0.1')
    """
    if not ip_candidates:
        return "127.0.0.1"

    valid_ips: List[str] = []
    for raw_ip in ip_candidates:
        ip_str = raw_ip.strip()
        if not ip_str or ip_str == "127.0.0.1" or ip_str.startswith("169.254."):
            continue
        try:
            ip_obj = ipaddress.IPv4Address(ip_str)
            if not ip_obj.is_loopback and not ip_obj.is_link_local:
                valid_ips.append(ip_str)
        except ValueError:
            continue

    if not valid_ips:
        return "127.0.0.1"

    # 우선순위 1: 192.168.x.x (사내 공유망 표준)
    for ip_str in valid_ips:
        if ip_str.startswith("192.168."):
            return ip_str

    # 우선순위 2: 10.x.x.x (사내 대규모망)
    for ip_str in valid_ips:
        if ip_str.startswith("10."):
            return ip_str

    # 우선순위 3: 172.16~31.x.x
    for ip_str in valid_ips:
        try:
            ip_obj = ipaddress.IPv4Address(ip_str)
            if ip_obj.is_private:
                return ip_str
        except ValueError:
            pass

    # 우선순위 4: 유효한 첫 번째 IP
    return valid_ips[0]


def is_printer_disabled(printer_name: Optional[str]) -> bool:
    """
    선택된 프린터 이름이 비활성화/제외/건너뛰기 대상인지 순수 판정합니다.

    Args:
        printer_name: 검사할 프린터 이름 (None, 빈 문자열, 또는 '(프린터 공유 안 함...)' 등)

    Returns:
        프린터 처리를 건너뛰어야 하면 True, 정상 공유 대상이면 False
    """
    if printer_name is None:
        return True
    
    clean_name = printer_name.strip()
    if not clean_name:
        return True

    # 괄호로 시작하는 Sentinel 안내 문구 예: '(프린터 공유 안 함...)', '(설치된 프린터가 없습니다)' 등
    if clean_name.startswith("(") or clean_name.startswith("["):
        return True

    return False


def format_printer_label(name: str, is_shared: bool) -> str:
    """
    프린터 이름과 공유 상태를 받아 사용자 친화적인 한글 UI 라벨을 생성합니다.

    Args:
        name: 프린터 실제 이름
        is_shared: 윈도우 네트워크 공유 여부 (True / False)

    Returns:
        화면 표시용 라벨 문자열 (예: 'Samsung ML-1640 [공유 중]' 또는 'Canon G3000')
    """
    clean_name = name.strip()
    if not clean_name:
        return ""
    if is_shared:
        return f"{clean_name} [공유 중]"
    return clean_name


def extract_actual_printer_name(display_label: Optional[str]) -> str:
    """
    UI 화면에 표시된 프린터 라벨에서 후미의 '[공유 중]' 뱃지를 제거하고 순수 프린터명을 추출합니다.

    Args:
        display_label: 드롭다운에서 선택된 문자열 (예: 'Samsung ML-1640 [공유 중]')

    Returns:
        실제 윈도우 프린터 명칭 (예: 'Samsung ML-1640')
    """
    if not display_label:
        return ""
    
    clean_label = display_label.strip()
    # 후미의 '[공유 중]' 또는 '[공유중]' 패턴 제거
    actual_name = re.sub(r'\s*\[공유\s*중\]$', '', clean_label)
    return actual_name.strip()

