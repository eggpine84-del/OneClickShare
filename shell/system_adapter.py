"""
Windows 시스템 제어 및 I/O 전담 어댑터 모듈
PowerShell, 레지스트리, WMI, 방화벽, 서비스, 파일 시스템 등의 실제 OS 조작을 담당합니다.
"""
import ctypes
import os
import socket
import subprocess
import sys
import winreg
import logging
from typing import List, Tuple, Optional, Dict, Any

from config import (
    DEFAULT_SHARE_FOLDER_PATH,
    DEFAULT_SHARE_NAME,
    DEFAULT_NETWORK_DRIVE_LETTER,
    DESKTOP_SHORTCUT_NAME,
    REQUIRED_SERVICES,
    REQUIRED_PORTS,
    FIREWALL_RULE_PREFIX,
    RPC_AUTHN_REG_PATH,
    RPC_AUTHN_KEY_NAME,
    RPC_AUTHN_DEFAULT_VALUE,
    LANMAN_WORKSTATION_REG_PATH,
    LANMAN_INSECURE_GUEST_KEY,
    LANMAN_INSECURE_GUEST_VALUE
)
from core.checker import (
    generate_powershell_firewall_command,
    generate_powershell_service_command,
    build_unc_path,
    is_valid_share_name,
    filter_preferred_local_ip
)
from shell.network_scanner import scan_network_for_shares
from shell.printer_adapter import (
    get_local_printers,
    share_printer,
    connect_remote_printer
)
from shell.registry_adapter import (
    is_admin,
    run_as_admin,
    apply_registry_fixes
)
from shell.folder_adapter import (
    create_folder_share,
    create_desktop_shortcut,
    map_network_drive,
    unshare_all
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)





def execute_powershell(command: str) -> Tuple[bool, str]:
    """
    PowerShell 명령어를 안전하게 실행하고 성공 여부와 출력을 반환합니다.

    Args:
        command: 실행할 PowerShell 스크립트 문자열

    Returns:
        (성공 여부 bool, 출력 또는 에러 문자열)
    """
    if not command or not command.strip():
        return False, "명령어가 비어 있습니다."

    try:
        full_command = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "{command}"'
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            shell=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            err_msg = result.stderr.strip() or result.stdout.strip()
            return False, err_msg
    except subprocess.TimeoutExpired:
        return False, "명령어 실행 시간 초과 (Timeout)"
    except Exception as e:
        return False, str(e)


def set_network_profile_private() -> Tuple[bool, str]:
    """
    현재 연결된 모든 네트워크 어댑터의 프로필을 '개인(Private)'으로 변경합니다.
    (공용 네트워크 상태에서는 방화벽이 공유를 차단하므로 필수적임)

    Returns:
        (성공 여부 bool, 메시지)
    """
    ps_cmd = "Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private -ErrorAction SilentlyContinue"
    success, output = execute_powershell(ps_cmd)
    if success:
        return True, "네트워크 프로필을 '개인(Private)'으로 성공적으로 전환했습니다."
    return False, f"네트워크 프로필 전환 실패: {output}"


def setup_services_and_firewall() -> Tuple[bool, List[str]]:
    """
    네트워크 탐색 및 공유에 필수적인 7대 서비스를 가동하고 방화벽 포트를 개방합니다.

    Returns:
        (전체 성공 여부 bool, 상세 로그 목록)
    """
    logs: List[str] = []
    all_success = True

    # 1. 7대 필수 서비스 가동 및 자동 시작 설정
    for svc_name, desc in REQUIRED_SERVICES:
        cmd = generate_powershell_service_command(svc_name)
        success, out = execute_powershell(cmd)
        if success:
            logs.append(f"[완료] 서비스 가동: {svc_name} ({desc})")
        else:
            logs.append(f"[주의] 서비스 가동 주의: {svc_name} ({desc})")

    # 2. 방화벽 기본 규칙 그룹 활성화
    enable_group_cmd = (
        'netsh advfirewall firewall set rule group="파일 및 프린터 공유" new enable=Yes; '
        'netsh advfirewall firewall set rule group="네트워크 검색" new enable=Yes'
    )
    execute_powershell(enable_group_cmd)

    # 3. 주요 포트 개별 개방
    for proto, port, desc in REQUIRED_PORTS:
        fw_cmd = generate_powershell_firewall_command(FIREWALL_RULE_PREFIX, proto, port)
        execute_powershell(fw_cmd)
        logs.append(f"[완료] 방화벽 포트 개방: {proto} {port} ({desc})")

    return all_success, logs











def get_local_ip_and_hostname() -> Tuple[str, str]:
    """
    현재 컴퓨터의 호스트 이름과 대표 로컬 IPv4 주소를 반환합니다.

    Returns:
        (호스트이름, IP주소)
    """
    hostname = socket.gethostname()
    candidates: List[str] = []

    # 1. 외부 라우팅 기반 소켓 IP 수집
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        sock_ip = s.getsockname()[0]
        s.close()
        if sock_ip:
            candidates.append(sock_ip)
    except Exception:
        pass

    # 2. 호스트명 기반 전체 인터페이스 IP 수집
    try:
        _, _, ip_list = socket.gethostbyname_ex(hostname)
        candidates.extend(ip_list)
    except Exception:
        pass

    # 3. Pure Core 함수를 통한 최적 사내망 IP 선별
    local_ip = filter_preferred_local_ip(candidates)
    return hostname, local_ip


def safe_copy_to_clipboard(root: Any, text: str) -> bool:
    """
    Tkinter 클립보드에 문자열을 안전하게 복사합니다.

    Args:
        root: Tkinter root 객체
        text: 클립보드에 복사할 문자열

    Returns:
        성공 여부 bool
    """
    if not text:
        return False
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        return True
    except Exception as e:
        logger.warning(f"클립보드 복사 예외: {e}")
        return False




