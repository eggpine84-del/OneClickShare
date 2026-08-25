"""
Windows 파일 및 폴더 공유, 네트워크 드라이브 및 바로가기 제어 전담 어댑터 모듈 (Shell)
SMB 폴더 공유 생성, 바탕화면 바로가기 생성, 네트워크 드라이브(Z:) 마운트 및 전체 공유 해제를 담당합니다.
"""
import os
import subprocess
import logging
from typing import List, Tuple, Optional

from config import (
    DEFAULT_SHARE_FOLDER_PATH,
    DEFAULT_SHARE_NAME,
    DEFAULT_NETWORK_DRIVE_LETTER,
    DESKTOP_SHORTCUT_NAME
)
from shell.printer_adapter import get_local_printers

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
            f"$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{shortcut_file}'); "
            f"$s.TargetPath = '{target_path}'; "
            f"$s.IconLocation = 'explorer.exe,0'; "
            f"$s.Save()"
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
    logs.append(f"[완료] 폴더 공유('{share_name}') 해제 완료")

    # 2. 모든 프린터 공유 해제
    printers = get_local_printers()
    for p_name, is_shared in printers:
        if is_shared:
            unshare_cmd = f'Set-Printer -Name "{p_name}" -Shared $false -ErrorAction SilentlyContinue'
            execute_powershell(unshare_cmd)
            logs.append(f"[완료] 프린터 '{p_name}' 공유 해제 완료")

    return True, logs
