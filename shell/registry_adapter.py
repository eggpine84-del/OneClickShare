"""
Windows 레지스트리 패치 및 UAC 권한 관리 어댑터 모듈 (Shell)
관리자 권한 확인 및 윈도우 10/11 RPC 오류(0x0000011b), 게스트 인증 레지스트리를 패치합니다.
"""
import ctypes
import os
import sys
import subprocess
import winreg
import logging
from typing import List, Tuple

from config import (
    RPC_AUTHN_REG_PATH,
    RPC_AUTHN_KEY_NAME,
    RPC_AUTHN_DEFAULT_VALUE,
    LANMAN_WORKSTATION_REG_PATH,
    LANMAN_INSECURE_GUEST_KEY,
    LANMAN_INSECURE_GUEST_VALUE
)

logger = logging.getLogger(__name__)


def is_admin() -> bool:
    """
    현재 프로세스가 Windows 관리자 권한으로 실행 중인지 확인합니다.

    Returns:
        관리자 권한이면 True, 아니면 False
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logger.warning(f"관리자 권한 확인 중 오류 발생: {e}")
        return False


def run_as_admin() -> None:
    """
    관리자 권한으로 프로그램을 스스로 다시 실행합니다 (UAC 창 팝업).
    """
    if is_admin():
        return
        
    try:
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"UAC 관리자 권한 승격 실패: {e}")


def apply_registry_fixes() -> Tuple[bool, List[str]]:
    """
    윈도우 10/11의 인쇄 스풀러 RPC 인증 오류(0x0000011b) 및 게스트 인증 차단 레지스트리를 패치합니다.

    Returns:
        (성공 여부 bool, 처리 로그 목록)
    """
    logs: List[str] = []
    
    # 1. RPC 인증 레벨 완화 (0x0000011b 오류 방지)
    try:
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, RPC_AUTHN_REG_PATH)
        winreg.SetValueEx(key, RPC_AUTHN_KEY_NAME, 0, winreg.REG_DWORD, RPC_AUTHN_DEFAULT_VALUE)
        winreg.CloseKey(key)
        logs.append(f"✅ 인쇄 RPC 레지스트리 패치 완료: {RPC_AUTHN_KEY_NAME}=0")
    except Exception as e:
        logs.append(f"⚠️ 인쇄 RPC 레지스트리 패치 실패: {e}")

    # 2. 안전하지 않은 게스트 로그온 허용 (암호 없는 공유 접속 허용)
    try:
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, LANMAN_WORKSTATION_REG_PATH)
        winreg.SetValueEx(key, LANMAN_INSECURE_GUEST_KEY, 0, winreg.REG_DWORD, LANMAN_INSECURE_GUEST_VALUE)
        winreg.CloseKey(key)
        logs.append(f"✅ 게스트 공유 접속 레지스트리 패치 완료: {LANMAN_INSECURE_GUEST_KEY}=1")
    except Exception as e:
        logs.append(f"⚠️ 게스트 공유 접속 레지스트리 패치 실패: {e}")

    # 스풀러 서비스 재시작으로 레지스트리 즉시 적용
    restart_cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Restart-Service -Name \'Spooler\' -Force -ErrorAction SilentlyContinue"'
    subprocess.run(restart_cmd, shell=True, capture_output=True)
    logs.append("✅ 인쇄 스풀러(Print Spooler) 서비스 재시작 완료")

    return True, logs
