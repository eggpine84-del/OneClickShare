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
        args = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
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


def get_local_printers() -> List[Tuple[str, bool]]:
    """
    현재 컴퓨터에 설치된 로컬 프린터 목록과 공유 여부를 조회합니다.

    Returns:
        [(프린터 이름, 공유 여부), ...] 목록
    """
    cmd = "Get-Printer | ForEach-Object { '{0};;{1}' -f $_.Name, $_.Shared }"
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
    PowerShell Add-Printer를 1순위로 실행하고 WScript.Network를 2순위 방어선으로 가동합니다.

    Args:
        host: 원격 호스트 이름 또는 IP
        printer_share_name: 프린터 공유 이름

    Returns:
        (성공 여부 bool, 메시지)
    """
    unc = build_unc_path(host, printer_share_name)
    if not unc:
        return False, "올바르지 않은 프린터 공유 경로입니다."

    # 1. PowerShell Add-Printer 1순위 다이렉트 연결 (최신 윈도우 10/11 표준)
    ps_cmd = f"Add-Printer -ConnectionName '{unc}' -ErrorAction Stop"
    success, out = execute_powershell(ps_cmd)
    if success:
        return True, f"공유 프린터('{unc}')가 성공적으로 등록되었습니다."

    # 2. WScript.Network 2차 방어선 시도
    vbs_cmd = f"(New-Object -ComObject WScript.Network).AddWindowsPrinterConnection('{unc}')"
    success_vbs, out_vbs = execute_powershell(vbs_cmd)
    if success_vbs:
        return True, f"공유 프린터('{unc}')가 WScript 연결로 등록되었습니다."

    # 3. PrintUI 3차 폴백 시도
    try:
        cmd = f'rundll32 printui.dll,PrintUIEntry /in /n"{unc}"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            return True, f"공유 프린터('{unc}') PrintUI 연결 요청 완료"
    except Exception:
        pass

    return False, f"프린터 연결 실패 ({unc}): {out or out_vbs}"


def get_remote_shared_printers(host_ip: str) -> List[str]:
    """
    원격 메인 PC에 공유되어 있는 프린터 목록을 조회합니다.

    Args:
        host_ip: 원격 메인 PC IP 주소 또는 호스트명

    Returns:
        공유된 프린터 이름 리스트
    """
    if not host_ip or host_ip == "127.0.0.1":
        return []

    printers: List[str] = []

    # 1. PowerShell 원격 프린터 쿼리 시도
    ps_cmd = f"Get-Printer -ComputerName '{host_ip}' -ErrorAction SilentlyContinue | Where-Object {{ $_.Shared -eq $true }} | ForEach-Object {{ $_.ShareName }}"
    success, out = execute_powershell(ps_cmd)
    if success and out:
        for line in out.splitlines():
            line_str = line.strip()
            if line_str and line_str not in printers:
                printers.append(line_str)

    if printers:
        return printers

    # 2. net view 폴백 시도
    try:
        net_cmd = f'net view "{host_ip}"'
        res = subprocess.run(net_cmd, shell=True, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "인쇄" in line or "Print" in line:
                    parts = line.split()
                    if parts:
                        p_name = parts[0].strip()
                        if p_name and p_name not in printers:
                            printers.append(p_name)
    except Exception:
        pass

    return printers

