"""
Tkinter 기반 모던 원클릭 GUI 인터페이스 모듈
직관적인 버튼과 실시간 로그 화면을 통해 누구나 쉽게 조작할 수 있는 그래픽 화면을 제공합니다.
"""
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Optional, List, Tuple

from config import (
    DEFAULT_SHARE_FOLDER_PATH,
    DEFAULT_SHARE_NAME,
    DEFAULT_NETWORK_DRIVE_LETTER,
    DESKTOP_SHORTCUT_NAME,
    OPTION_NO_PRINTER_HOST,
    OPTION_NO_PRINTER_CLIENT
)
from core.checker import build_unc_path, is_valid_share_name, is_printer_disabled
from shell.system_adapter import (
    get_local_ip_and_hostname,
    set_network_profile_private,
    setup_services_and_firewall,
    apply_registry_fixes,
    get_local_printers,
    share_printer,
    create_folder_share,
    create_desktop_shortcut,
    map_network_drive,
    connect_remote_printer,
    unshare_all,
    scan_network_for_shares,
    safe_copy_to_clipboard
)
from shell.printer_adapter import get_remote_shared_printers
from shell.gui_tabs import (
    build_host_tab,
    build_client_tab,
    build_diag_tab,
    build_unshare_tab
)
from shell.gui_banner import build_top_banner_card


class OneClickShareApp:
    """
    원클릭 사내 공유 매니저 메인 GUI 애플리케이션 클래스
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("원클릭 사내 프린터 & 폴더 공유 매니저")
        self.root.geometry("720x680")
        self.root.minsize(680, 600)

        # 시스템 정보 획득
        self.hostname, self.local_ip = get_local_ip_and_hostname()

        self._setup_style()
        self._build_ui()
        self._refresh_printers()
        # 시작 시 사내 네트워크의 메인 PC 자동 백그라운드 탐색
        self._run_in_thread(self._auto_scan_main_pc)

    def _setup_style(self) -> None:
        """UI 테마 및 스타일을 설정합니다."""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # 폰트 및 여백 스타일 설정
        self.style.configure("TNotebook.Tab", font=("Malgun Gothic", 10, "bold"), padding=[12, 6])
        self.style.configure("Primary.TButton", font=("Malgun Gothic", 10, "bold"), padding=6)
        self.style.configure("Header.TLabel", font=("Malgun Gothic", 11, "bold"))
        self.style.configure("Info.TLabel", font=("Malgun Gothic", 9))

    def _build_ui(self) -> None:
        """전체 UI 레이아웃을 생성합니다."""
        # 1. 상단 내 컴퓨터 정보 배너 (강조 카드)
        self.top_card = build_top_banner_card(self, self.root)

        # 2. 탭 컨테이너
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 각 탭 프레임 생성
        self.tab_host = ttk.Frame(self.notebook, padding=15)
        self.tab_client = ttk.Frame(self.notebook, padding=15)
        self.tab_diag = ttk.Frame(self.notebook, padding=15)
        self.tab_unshare = ttk.Frame(self.notebook, padding=15)

        self.notebook.add(self.tab_host, text="[메인 PC] 공유 설정")
        self.notebook.add(self.tab_client, text="[직원 PC] 공유 연결")
        self.notebook.add(self.tab_diag, text="[자동 진단] 원클릭 복구")
        self.notebook.add(self.tab_unshare, text="[초기화] 공유 전체 해제")

        build_host_tab(self, self.tab_host)
        build_client_tab(self, self.tab_client)
        build_diag_tab(self, self.tab_diag)
        build_unshare_tab(self, self.tab_unshare)

        # 3. 하단 실시간 로그 창
        log_frame = ttk.LabelFrame(self.root, text=" [진행 로그] ", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(5, 10))

        self.log_area = scrolledtext.ScrolledText(
            log_frame,
            height=8,
            font=("Consolas", 9),
            bg="#f8fafc",
            fg="#1e293b",
            state=tk.DISABLED
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def log(self, message: str) -> None:
        """로그 창에 메시지를 출력합니다."""
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"{message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def _action_copy_ip(self) -> None:
        """내 IP 주소를 클립보드에 복사합니다."""
        if safe_copy_to_clipboard(self.root, self.local_ip):
            self.log(f"[클립보드] 내 IP 주소 '{self.local_ip}'가 복사되었습니다. (상대방에게 전달하세요)")
        else:
            self.log("[오류] IP 복사 실패")

    def _action_copy_share_path(self) -> None:
        """내 공유 폴더 접속 경로(UNC)를 클립보드에 복사합니다."""
        unc_path = build_unc_path(self.local_ip, DEFAULT_SHARE_NAME)
        if safe_copy_to_clipboard(self.root, unc_path):
            self.log(f"[클립보드] 접속 경로 '{unc_path}'가 복사되었습니다. (직원 PC 탐색기 주소창에 붙여넣기 가능)")
        else:
            self.log("[오류] 접속 경로 복사 실패")

    def _refresh_printers(self) -> None:
        """로컬 프린터 목록을 갱신합니다."""
        printers = get_local_printers()
        printer_names = [name for name, _ in printers]
        options = [OPTION_NO_PRINTER_HOST] + printer_names
        self.printer_combo["values"] = options
        if printer_names:
            self.printer_combo.current(1)
        else:
            self.printer_combo.current(0)

    def _action_setup_host(self) -> None:
        """메인 PC 원클릭 설정 동작"""
        self.log("--- [메인 PC] 공유 설정 시작 ---")
        self.log("1. 사내 네트워크 프로필을 '개인(Private)'으로 전환 중...")
        _, msg = set_network_profile_private()
        self.log(f"   ➜ {msg}")

        self.log("2. 윈도우 탐색 7대 서비스 가동 및 방화벽 포트 개방 중...")
        _, svc_logs = setup_services_and_firewall()
        for l in svc_logs:
            self.log(f"   ➜ {l}")

        self.log("3. 윈도우 10/11 공유 오류 방지 레지스트리 패치 적용 중...")
        _, reg_logs = apply_registry_fixes()
        for l in reg_logs:
            self.log(f"   ➜ {l}")

        folder_path = self.txt_folder_path.get().strip()
        share_name = self.txt_share_name.get().strip()
        self.log(f"4. 공유 폴더 생성 중: {folder_path} (공유명: {share_name})...")
        f_ok, f_msg = create_folder_share(folder_path, share_name)
        self.log(f"   ➜ {f_msg}")

        selected_printer = self.printer_combo.get()
        if not is_printer_disabled(selected_printer):
            self.log(f"5. 프린터 '{selected_printer}' 네트워크 공유 설정 중...")
            p_ok, p_msg = share_printer(selected_printer)
            self.log(f"   ➜ {p_msg}")
        else:
            self.log("5. [프린터 제외] 프린터 공유를 건너뛰고 파일 공유 폴더만 단독 설정합니다.")

        unc_folder = build_unc_path(self.hostname, share_name)
        self.log("--- [완료] 메인 PC 설정이 완료되었습니다 ---")
        self.log(f"[접속 주소] {unc_folder} (또는 \\\\{self.local_ip}\\{share_name})")
        messagebox.showinfo("설정 완료", f"메인 PC 설정이 완료되었습니다!\n\n접속 주소: {unc_folder}\n로컬 IP: {self.local_ip}")

    def _auto_scan_main_pc(self) -> None:
        """사내 네트워크에서 공유 중인 메인 PC를 자동 탐색하여 콤보박스에 반영합니다."""
        self.log("[탐색] 사내 네트워크의 공유 메인 PC를 탐색 중...")
        found_hosts = scan_network_for_shares(self.local_ip)
        
        display_values: List[str] = []
        for h_name, h_ip in found_hosts:
            display_values.append(f"{h_ip} ({h_name})")

        if not display_values:
            display_values = [f"{self.local_ip} (내 컴퓨터/기본값)"]

        def update_ui():
            self.scanned_host_combo["values"] = display_values
            self.scanned_host_combo.current(0)
            self._on_select_scanned_host(None)
            self.log(f"[완료] 사내 메인 PC 탐색 완료 ({len(found_hosts)}대 발견)")

        self.root.after(0, update_ui)

    def _on_select_scanned_host(self, event) -> None:
        """드롭다운에서 메인 PC를 선택했을 때 입력 필드에 자동 주입하고 원격 프린터를 자동 감지합니다."""
        selected = self.scanned_host_combo.get()
        if selected and "(" in selected:
            ip_part = selected.split("(")[0].strip()
            self.txt_target_host.delete(0, tk.END)
            self.txt_target_host.insert(0, ip_part)
            self._run_in_thread(lambda: self._fetch_remote_printers(ip_part))

    def _fetch_remote_printers_from_input(self) -> None:
        """현재 입력창의 메인 PC 주소로 원격 프린터를 검색합니다."""
        host_ip = self.txt_target_host.get().strip()
        if host_ip:
            self._fetch_remote_printers(host_ip)

    def _fetch_remote_printers(self, host_ip: str) -> None:
        """원격 메인 PC에 공유된 프린터 목록을 조회하여 콤보박스에 자동 반영합니다."""
        self.log(f"[프린터 탐색] 메인 PC({host_ip})의 공유 프린터 조회 중...")
        printers = get_remote_shared_printers(host_ip)
        
        def update_printer_ui():
            if printers:
                self.client_printer_combo["values"] = [OPTION_NO_PRINTER_CLIENT] + printers
                self.client_printer_combo.current(1)
                self.log(f"[완료] 메인 PC 공유 프린터 {len(printers)}개 감지 완료 ({', '.join(printers)})")
            else:
                self.client_printer_combo["values"] = [OPTION_NO_PRINTER_CLIENT, "(공유된 프린터가 없습니다)"]
                self.client_printer_combo.current(0)
                self.log("[안내] 메인 PC에 공유된 프린터가 없습니다. (폴더만 연결 가능)")

        self.root.after(0, update_printer_ui)

    def _action_connect_client(self) -> None:
        """직원 PC 원클릭 연결 동작"""
        target_host = self.txt_target_host.get().strip()
        share_name = self.txt_client_share_name.get().strip()
        
        raw_printer = self.client_printer_combo.get().strip()
        printer_disabled = is_printer_disabled(raw_printer)

        if not target_host:
            messagebox.showwarning("입력 필요", "메인 PC의 컴퓨터 이름 또는 IP 주소를 입력해 주세요.")
            return

        self.log(f"--- [직원 PC] 메인 PC({target_host}) 연결 시작 ---")
        self.log("1. 연결용 레지스트리 및 서비스 준비 중...")
        apply_registry_fixes()

        unc_folder = build_unc_path(target_host, share_name)
        self.log(f"2. 공유 폴더 경로 확인: {unc_folder}")

        if self.chk_shortcut_var.get():
            self.log("   ➜ 바탕화면 바로가기 생성 중...")
            _, s_msg = create_desktop_shortcut(unc_folder)
            self.log(f"   ➜ {s_msg}")

        if self.chk_drive_var.get():
            self.log(f"   ➜ {DEFAULT_NETWORK_DRIVE_LETTER} 드라이브로 마운트 중...")
            _, d_msg = map_network_drive(unc_folder)
            self.log(f"   ➜ {d_msg}")

        if not printer_disabled:
            self.log(f"3. 공유 프린터('{raw_printer}') 등록 시도 중...")
            _, p_msg = connect_remote_printer(target_host, raw_printer)
            self.log(f"   ➜ {p_msg}")
        else:
            self.log("3. [프린터 제외] 프린터 연결을 건너뛰고 공용 폴더만 연결합니다...")

        os.system(f'explorer.exe "{unc_folder}"')
        self.log("--- [완료] 메인 PC 연결 작업이 완료되었습니다 ---")
        messagebox.showinfo("연결 완료", f"메인 PC({target_host}) 연결이 완료되었습니다!\n공용 폴더 창이 열립니다.")

    def _action_run_diag(self) -> None:
        """자가 진단 및 자동 복구 동작"""
        self.log("--- [자동 진단] 원클릭 진단 및 복구 시작 ---")
        set_network_profile_private()
        setup_services_and_firewall()
        apply_registry_fixes()
        self.log("--- [완료] 모든 공유 설정과 방화벽이 정상 복구되었습니다 ---")
        messagebox.showinfo("복구 완료", "네트워크 공유 환경과 레지스트리가 정상 복구되었습니다.")

    def _action_run_unshare(self) -> None:
        """공유 해제 동작"""
        if not messagebox.askyesno("공유 해제 확인", "정말로 이 컴퓨터의 폴더 및 프린터 공유를 해제하시겠습니까?"):
            return
            
        self.log("--- [초기화] 공유 해제 진행 중 ---")
        _, logs = unshare_all(DEFAULT_SHARE_NAME)
        for l in logs:
            self.log(f"   ➜ {l}")
        self.log("--- [완료] 공유 해제가 완료되었습니다 ---")
        messagebox.showinfo("해제 완료", "이 컴퓨터의 공유가 모두 해제되었습니다.")

    def _run_in_thread(self, target_func) -> None:
        """UI가 멈추지 않도록 백그라운드 스레드에서 작업을 실행합니다."""
        t = threading.Thread(target=target_func, daemon=True)
        t.start()
