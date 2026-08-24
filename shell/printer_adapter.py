"""
Windows 프린터 제어 및 Spooler 연동 어댑터 모듈 (Shell)
로컬 프린터 조회, 네트워크 공유 설정, 원격 프린터 연결을 담당합니다.
"""
import subprocess
import logging
from typing import List, Tuple, Optional

from core.checker import parse_printer_list_output, build_unc_path

logger = logging.getLogger(__name__)


def execute_powershell(command: str) -> Tuple[bool, str]:
    """
    PowerShell 명령어를 안전하게 실행하고 성공 여부와 출력을 반환합니다.
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


def get_local_printers() -> List[Tuple[str, bool]]:
    """
    현재 컴퓨터에 설치된 로컬 프린터 목록과 공유 여부를 조회합니다.

    Returns:
        [(프린터 이름, 공유 여부), ...] 목록
    """
    cmd = 'Get-Printer | ForEach-Object { "$($_.Name);;$($_.Shared)" }'
    success, output = execute_powershell(cmd)
    if not success or not output:
        return []
    return parse_printer_list_output(output)


def share_printer(printer_name: str, share_name: Optional[str] = None) -> Tuple[bool, str]:
    """
    지정된 로컬 프린터를 네트워크에 공유 설정합니다.

    Args:
        printer_name: 프린터 이름
        share_name: 공유명 (생략 시 프린터 이름으로 설정)

    Returns:
        (성공 여부 bool, 메시지)
    """
    target_share = share_name if share_name else printer_name
    cmd = f'Set-Printer -Name "{printer_name}" -Shared $true -ShareName "{target_share}" -ErrorAction Stop'
    success, out = execute_powershell(cmd)
    if success:
        return True, f"프린터 '{printer_name}'이(가) '{target_share}' 이름으로 공유되었습니다."
    return False, f"프린터 공유 설정 실패: {out}"


def connect_remote_printer(host: str, printer_share_name: str) -> Tuple[bool, str]:
    """
    원격 호스트의 공유 프린터를 로컬 컴퓨터에 연결 및 등록합니다.

    Args:
        host: 원격 호스트 이름 또는 IP
        printer_share_name: 프린터 공유 이름

    Returns:
        (성공 여부 bool, 메시지)
    """
    unc = build_unc_path(host, printer_share_name)
    if not unc:
        return False, "올바르지 않은 프린터 공유 경로입니다."

    # Windows PrintUI를 통한 원격 프린터 연결
    cmd = f'rundll32 printui.dll,PrintUIEntry /in /n"{unc}"'
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
        if res.returncode == 0:
            return True, f"공유 프린터('{unc}') 연결이 완료되었습니다."
        
        # PowerShell Fallback 시도
        ps_cmd = f'Add-Printer -ConnectionName "{unc}" -ErrorAction Stop'
        success, out = execute_powershell(ps_cmd)
        if success:
            return True, f"공유 프린터('{unc}')가 등록되었습니다."
        return False, f"프린터 연결 실패 ({unc}): {out or res.stderr}"
    except Exception as e:
        return False, f"프린터 연결 중 예외 발생: {e}"
