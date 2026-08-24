"""
환경 설정 및 시스템 상수 정의 모듈
하드코딩을 방지하고 환경 변수 및 고정 설정값을 일원화하여 관리합니다.
"""
import os
from typing import List, Tuple

# ==========================================
# 1. 파일 및 폴더 공유 기본 설정
# ==========================================
# 기본 공유 폴더 생성 위치
DEFAULT_SHARE_FOLDER_PATH: str = r"C:\회사공용폴더"

# SMB 네트워크 공유 이름
DEFAULT_SHARE_NAME: str = "CompanyShare"

# 클라이언트 PC 연결 시 사용할 기본 드라이브 문자 (네트워크 드라이브)
DEFAULT_NETWORK_DRIVE_LETTER: str = "Z:"

# 바탕화면 바로가기 파일 이름
DESKTOP_SHORTCUT_NAME: str = "회사 공용폴더.lnk"

# ==========================================
# 2. 윈도우 필수 탐색 7대 서비스 목록
# ==========================================
# (서비스 영문명, 한글 설명)
REQUIRED_SERVICES: List[Tuple[str, str]] = [
    ("FDResPub", "함수 검색 리소스 출판 (네트워크에 내 PC 검색 가능하게 함)"),
    ("FDPHost", "함수 검색 공급자 호스트 (상대방 PC 탐색 지원)"),
    ("LanmanServer", "서버 서비스 (내 폴더/프린터를 다른 컴퓨터에 공유)"),
    ("LanmanWorkstation", "워크스테이션 서비스 (상대방 공유 자원에 접속)"),
    ("SSDPSRV", "SSDP 탐색 (네트워크 장치 자동 발견)"),
    ("upnphost", "UPnP 장치 호스트 (범용 플러그 앤 플레이 지원)"),
    ("Dnscache", "DNS 클라이언트 (컴퓨터 이름/IP 확인)")
]

# ==========================================
# 3. 방화벽 규칙 및 포트 설정
# ==========================================
FIREWALL_RULE_PREFIX: str = "OneClickShare"

# 개방할 주요 포트 (프로토콜, 포트번호, 설명)
REQUIRED_PORTS: List[Tuple[str, int, str]] = [
    ("TCP", 445, "SMB 파일 및 프린터 공유"),
    ("TCP", 139, "NetBIOS 세션 서비스"),
    ("UDP", 137, "NetBIOS 이름 서비스"),
    ("UDP", 138, "NetBIOS 데이터그램 서비스"),
    ("UDP", 3702, "WSD 네트워크 장치 탐색"),
    ("UDP", 5355, "LLMNR 로컬 링크 이름 확인")
]

# ==========================================
# 4. 윈도우 10/11 고질적 오류 해결용 레지스트리 경로
# ==========================================
# 0x0000011b 인쇄 스풀러 RPC 인증 완화 패치
RPC_AUTHN_REG_PATH: str = r"System\CurrentControlSet\Control\Print"
RPC_AUTHN_KEY_NAME: str = "RpcAuthnLevelExemption"
RPC_AUTHN_DEFAULT_VALUE: int = 0

# 게스트(비밀번호 없는 계정) 접속 차단 완화 패치
LANMAN_WORKSTATION_REG_PATH: str = r"System\CurrentControlSet\Services\LanmanWorkstation\Parameters"
LANMAN_INSECURE_GUEST_KEY: str = "AllowInsecureGuestAuth"
LANMAN_INSECURE_GUEST_VALUE: int = 1
