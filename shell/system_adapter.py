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
    is_valid_share_name
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
            timeout=30
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
            logs.append(f"✅ 서비스 가동 완료: {svc_name} ({desc})")
        else:
            logs.append(f"⚠️ 서비스 가동 주의: {svc_name} ({desc})")

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
        logs.append(f"✅ 방화벽 포트 개방: {proto} {port} ({desc})")

    return all_success, logs








def create_folder_share(folder_path: str = DEFAULT_SHARE_FOLDER_PATH, share_name: str = DEFAULT_SHARE_NAME) -> Tuple[bool, str]:
    """
    지정한 폴더를 생성하고, Everyone 읽기/쓰기 권한으로 SMB 공유를 생성합니다.

    Args:
        folder_path: 공유할 로컬 폴더 경로
        share_name: SMB 공유 이름

    Returns:
        (성공 여부 bool, 메시지)
    """
    try:
        # 폴더 생성
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)

        # NTFS 권한 부여 (Everyone에 모든 권한)
        icacls_cmd = f'icacls "{folder_path}" /grant "Everyone:(OI)(CI)F" /T /C /Q'
        subprocess.run(icacls_cmd, shell=True, capture_output=True)

        # SMB 공유 생성 (기존 공유가 있으면 삭제 후 재생성)
        remove_share_cmd = f'Remove-SmbShare -Name "{share_name}" -Force -ErrorAction SilentlyContinue'
        execute_powershell(remove_share_cmd)

        add_share_cmd = (
            f'New-SmbShare -Name "{share_name}" -Path "{folder_path}" '
            f'-FullAccess "Everyone" -ErrorAction Stop'
        )
        success, out = execute_powershell(add_share_cmd)
        if success:
            return True, f"폴더 '{folder_path}'이(가) 공유명 '{share_name}'으로 성공적으로 등록되었습니다."
        return False, f"SMB 폴더 공유 등록 실패: {out}"
    except Exception as e:
        return False, f"공유 폴더 처리 중 오류 발생: {e}"


def get_local_ip_and_hostname() -> Tuple[str, str]:
    """
    현재 컴퓨터의 호스트 이름과 대표 로컬 IPv4 주소를 반환합니다.

    Returns:
        (호스트이름, IP주소)
    """
    hostname = socket.gethostname()
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 외부 연결 시도를 통해 실제 라우팅되는 로컬 IP 추출
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        try:
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "127.0.0.1"
    return hostname, local_ip


def create_desktop_shortcut(target_path: str, shortcut_name: str = DESKTOP_SHORTCUT_NAME) -> Tuple[bool, str]:
    """
    바탕화면에 지정된 네트워크 폴더 UNC 경로를 가리키는 바로가기(.lnk)를 생성합니다.

    Args:
        target_path: 바로가기가 가리킬 UNC 경로 (예: \\192.168.0.10\CompanyShare)
        shortcut_name: 바로가기 파일명

    Returns:
        (성공 여부 bool, 메시지)
    """
    try:
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop_dir):
            # 한글 윈도우 바탕화면 경로 폴백
            desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "바탕 화면")

        shortcut_file = os.path.join(desktop_dir, shortcut_name)
        
        vbs_cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut_file}"); '
            f'$s.TargetPath = "{target_path}"; '
            f'$s.IconLocation = "explorer.exe,0"; '
            f'$s.Save()'
        )
        success, out = execute_powershell(vbs_cmd)
        if success:
            return True, f"바탕화면에 '{shortcut_name}' 바로가기가 생성되었습니다."
        return False, f"바로가기 생성 실패: {out}"
    except Exception as e:
        return False, f"바로가기 생성 중 예외: {e}"


def map_network_drive(unc_path: str, drive_letter: str = DEFAULT_NETWORK_DRIVE_LETTER) -> Tuple[bool, str]:
    """
    지정된 UNC 경로를 네트워크 드라이브(Z:)로 마운트합니다.

    Args:
        unc_path: 공유 폴더 UNC 경로
        drive_letter: 드라이브 문자 (예: 'Z:')

    Returns:
        (성공 여부 bool, 메시지)
    """
    try:
        # 기존 드라이브 연결 해제
        disconnect_cmd = f"net use {drive_letter} /delete /y"
        subprocess.run(disconnect_cmd, shell=True, capture_output=True)

        # 새 드라이브 연결
        connect_cmd = f'net use {drive_letter} "{unc_path}" /persistent:yes'
        res = subprocess.run(connect_cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            return True, f"네트워크 드라이브({drive_letter})로 정상 연결되었습니다."
        return False, f"네트워크 드라이브 연결 실패: {res.stderr.strip()}"
    except Exception as e:
        return False, f"네트워크 드라이브 매핑 중 오류: {e}"





def unshare_all(share_name: str = DEFAULT_SHARE_NAME) -> Tuple[bool, List[str]]:
    """
    현재 컴퓨터의 SMB 폴더 공유를 닫고 모든 프린터의 공유 속성을 해제합니다.

    Returns:
        (성공 여부 bool, 로그 목록)
    """
    logs: List[str] = []
    
    # 1. SMB 폴더 공유 삭제
    rm_cmd = f'Remove-SmbShare -Name "{share_name}" -Force -ErrorAction SilentlyContinue'
    execute_powershell(rm_cmd)
    logs.append(f"✅ 폴더 공유('{share_name}') 해제 완료")

    # 2. 모든 프린터 공유 해제
    printers = get_local_printers()
    for p_name, is_shared in printers:
        if is_shared:
            unshare_cmd = f'Set-Printer -Name "{p_name}" -Shared $false -ErrorAction SilentlyContinue'
            execute_powershell(unshare_cmd)
            logs.append(f"✅ 프린터 '{p_name}' 공유 해제 완료")

    return True, logs

