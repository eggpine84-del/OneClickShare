"""
사내 네트워크 고속 병렬 스캔 모듈 (Shell)
사내 서브넷 내 공유 포트(445)가 열려 있는 메인 PC를 감지합니다.
"""
import socket
import concurrent.futures
import logging
from typing import List, Tuple, Optional

from core.checker import generate_subnet_ip_list

logger = logging.getLogger(__name__)


def _check_smb_host(ip: str, timeout: float = 0.5) -> Optional[Tuple[str, str]]:
    """
    단일 IP에 대해 SMB(445) 포트 오픈 여부를 확인하고 호스트명을 조회합니다.

    Args:
        ip: 대상 IP 주소
        timeout: 소켓 타임아웃 초

    Returns:
        (호스트명, IP) 또는 감지 실패 시 None
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, 445))
        sock.close()
        if result == 0:
            try:
                host_name = socket.gethostbyaddr(ip)[0]
            except Exception:
                host_name = ip
            return (host_name, ip)
    except (ConnectionAbortedError, ConnectionResetError, OSError):
        pass
    except Exception as e:
        logger.debug(f"호스트 스캔 중 예외: {e}")
    return None


def scan_network_for_shares(local_ip: str, max_workers: int = 50) -> List[Tuple[str, str]]:
    """
    사내 로컬 서브넷 전체를 멀티스레드로 고속 스캔하여 공유 포트(445)가 열려 있는 메인 PC 목록을 반환합니다.

    Args:
        local_ip: 현재 컴퓨터의 로컬 IP (예: '192.168.0.15')
        max_workers: 병렬 스레드 수 (기본값: 50)

    Returns:
        [(호스트명, IP주소), ...] 목록
    """
    # Guard Clause: 대상 IP 목록 생성
    target_ips = generate_subnet_ip_list(local_ip)
    found_hosts: List[Tuple[str, str]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ip = {executor.submit(_check_smb_host, ip): ip for ip in target_ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            res = future.result()
            if res:
                found_hosts.append(res)

    return found_hosts
