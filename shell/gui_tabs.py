"""
Tkinter 탭 UI 레이아웃 빌더 모듈 (View)
4대 기능 탭(메인 PC 탭, 직원 PC 탭, 진단 탭, 공유 해제 탭)의 위젯 및 레이아웃을 생성합니다.
"""
import tkinter as tk
from tkinter import ttk
from typing import Any

from config import (
    DEFAULT_SHARE_FOLDER_PATH,
    DEFAULT_SHARE_NAME,
    DEFAULT_NETWORK_DRIVE_LETTER
)


def build_host_tab(app: Any, parent: ttk.Frame) -> None:
    """메인 PC (호스트) 탭 레이아웃을 생성합니다."""
    desc_lbl = ttk.Label(
        parent,
        text="이 컴퓨터(메인 PC)의 프린터와 폴더를 다른 직원이 접근할 수 있도록 1초 만에 설정합니다.",
        foreground="#2563eb",
        style="Header.TLabel"
    )
    desc_lbl.pack(anchor="w", pady=(0, 10))

    # 프린터 선택 영역
    p_frame = ttk.LabelFrame(parent, text=" 🖨️ 공유할 프린터 선택 ", padding=10)
    p_frame.pack(fill=tk.X, pady=5)

    app.printer_combo = ttk.Combobox(p_frame, state="readonly", width=50)
    app.printer_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

    btn_refresh = ttk.Button(p_frame, text="새로고침", command=app._refresh_printers)
    btn_refresh.pack(side=tk.RIGHT)

    # 폴더 설정 영역
    f_frame = ttk.LabelFrame(parent, text=" 📁 공유할 폴더 설정 ", padding=10)
    f_frame.pack(fill=tk.X, pady=5)

    ttk.Label(f_frame, text="폴더 경로:").grid(row=0, column=0, sticky="w", pady=2)
    app.txt_folder_path = ttk.Entry(f_frame, width=45)
    app.txt_folder_path.insert(0, DEFAULT_SHARE_FOLDER_PATH)
    app.txt_folder_path.grid(row=0, column=1, padx=5, pady=2, sticky="we")

    ttk.Label(f_frame, text="공유 이름:").grid(row=1, column=0, sticky="w", pady=2)
    app.txt_share_name = ttk.Entry(f_frame, width=45)
    app.txt_share_name.insert(0, DEFAULT_SHARE_NAME)
    app.txt_share_name.grid(row=1, column=1, padx=5, pady=2, sticky="we")

    # 실행 버튼
    btn_start_host = tk.Button(
        parent,
        text="🚀 내 컴퓨터를 메인으로 원클릭 설정하기",
        font=("Malgun Gothic", 12, "bold"),
        bg="#2563eb",
        fg="white",
        activebackground="#1d4ed8",
        activeforeground="white",
        relief=tk.RAISED,
        cursor="hand2",
        pady=10,
        command=lambda: app._run_in_thread(app._action_setup_host)
    )
    btn_start_host.pack(fill=tk.X, pady=(15, 0))


def build_client_tab(app: Any, parent: ttk.Frame) -> None:
    """직원 PC (클라이언트) 탭 레이아웃을 생성합니다."""
    desc_lbl = ttk.Label(
        parent,
        text="메인 PC의 프린터와 공용 폴더를 내 컴퓨터에 즉시 연결하고 바탕화면에 바로가기를 만듭니다.",
        foreground="#16a34a",
        style="Header.TLabel"
    )
    desc_lbl.pack(anchor="w", pady=(0, 10))

    # 메인 PC 자동 감지 및 선택 영역
    auto_frame = ttk.LabelFrame(parent, text=" 🔍 사내 메인 PC 자동 감지 ", padding=10)
    auto_frame.pack(fill=tk.X, pady=5)

    ttk.Label(auto_frame, text="발견된 메인 PC:").pack(anchor="w", pady=(0, 2))
    sub_auto = ttk.Frame(auto_frame)
    sub_auto.pack(fill=tk.X)

    app.scanned_host_combo = ttk.Combobox(sub_auto, state="readonly", width=45)
    app.scanned_host_combo["values"] = ["(네트워크 탐색 중...)"]
    app.scanned_host_combo.current(0)
    app.scanned_host_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
    app.scanned_host_combo.bind("<<ComboboxSelected>>", app._on_select_scanned_host)

    btn_rescan = ttk.Button(
        sub_auto,
        text="다시 검색",
        command=lambda: app._run_in_thread(app._auto_scan_main_pc)
    )
    btn_rescan.pack(side=tk.RIGHT)

    # 수동 주소 입력 영역 (폴백)
    c_frame = ttk.LabelFrame(parent, text=" 🎯 메인 PC 상세 정보 ", padding=10)
    c_frame.pack(fill=tk.X, pady=5)

    ttk.Label(c_frame, text="메인 PC 이름 또는 IP:").grid(row=0, column=0, sticky="w", pady=4)
    app.txt_target_host = ttk.Entry(c_frame, width=35)
    app.txt_target_host.insert(0, app.local_ip)
    app.txt_target_host.grid(row=0, column=1, padx=5, pady=4, sticky="we")

    ttk.Label(c_frame, text="공유 폴더 이름:").grid(row=1, column=0, sticky="w", pady=4)
    app.txt_client_share_name = ttk.Entry(c_frame, width=35)
    app.txt_client_share_name.insert(0, DEFAULT_SHARE_NAME)
    app.txt_client_share_name.grid(row=1, column=1, padx=5, pady=4, sticky="we")

    ttk.Label(c_frame, text="공유 프린터 이름:").grid(row=2, column=0, sticky="w", pady=4)
    app.txt_client_printer_name = ttk.Entry(c_frame, width=35)
    app.txt_client_printer_name.grid(row=2, column=1, padx=5, pady=4, sticky="we")
    ttk.Label(c_frame, text="(모르면 빈칸으로 두셔도 됩니다)", foreground="#6b7280").grid(row=2, column=2, sticky="w")

    # 연결 옵션 체크박스
    opt_frame = ttk.Frame(parent, padding=5)
    opt_frame.pack(fill=tk.X, pady=5)

    app.chk_shortcut_var = tk.BooleanVar(value=True)
    app.chk_shortcut = ttk.Checkbutton(opt_frame, text="바탕화면에 '📁 회사 공용폴더' 바로가기 생성", variable=app.chk_shortcut_var)
    app.chk_shortcut.pack(anchor="w")

    app.chk_drive_var = tk.BooleanVar(value=True)
    app.chk_drive = ttk.Checkbutton(opt_frame, text=f"내 컴퓨터에 '{DEFAULT_NETWORK_DRIVE_LETTER}' 네트워크 드라이브로 연결", variable=app.chk_drive_var)
    app.chk_drive.pack(anchor="w")

    # 원클릭 연결 버튼
    btn_start_client = tk.Button(
        parent,
        text="⚡ 메인 PC 프린터 & 폴더 원클릭 연결하기",
        font=("Malgun Gothic", 12, "bold"),
        bg="#16a34a",
        fg="white",
        activebackground="#15803d",
        activeforeground="white",
        relief=tk.RAISED,
        cursor="hand2",
        pady=10,
        command=lambda: app._run_in_thread(app._action_connect_client)
    )
    btn_start_client.pack(fill=tk.X, pady=(15, 0))


def build_diag_tab(app: Any, parent: ttk.Frame) -> None:
    """원클릭 진단 & 해결 탭 레이아웃을 생성합니다."""
    desc_lbl = ttk.Label(
        parent,
        text="네트워크 공유가 안 되거나 프린터 연결 오류(0x0000011b 등)가 발생할 때 자동 복구합니다.",
        foreground="#d97706",
        style="Header.TLabel"
    )
    desc_lbl.pack(anchor="w", pady=(0, 10))

    btn_run_diag = tk.Button(
        parent,
        text="🩺 네트워크 & 공유 오류 원클릭 자동 복구하기",
        font=("Malgun Gothic", 12, "bold"),
        bg="#d97706",
        fg="white",
        activebackground="#b45309",
        activeforeground="white",
        relief=tk.RAISED,
        cursor="hand2",
        pady=10,
        command=lambda: app._run_in_thread(app._action_run_diag)
    )
    btn_run_diag.pack(fill=tk.X, pady=10)


def build_unshare_tab(app: Any, parent: ttk.Frame) -> None:
    """공유 해제 (초기화) 탭 레이아웃을 생성합니다."""
    desc_lbl = ttk.Label(
        parent,
        text="메인 PC를 다른 컴퓨터로 바꿀 때, 이 컴퓨터의 기존 공유를 깨끗하게 닫습니다.",
        foreground="#dc2626",
        style="Header.TLabel"
    )
    desc_lbl.pack(anchor="w", pady=(0, 10))

    btn_run_unshare = tk.Button(
        parent,
        text="🧹 이 컴퓨터의 모든 공유 해제 (초기화)",
        font=("Malgun Gothic", 12, "bold"),
        bg="#dc2626",
        fg="white",
        activebackground="#b91c1c",
        activeforeground="white",
        relief=tk.RAISED,
        cursor="hand2",
        pady=10,
        command=lambda: app._run_in_thread(app._action_run_unshare)
    )
    btn_run_unshare.pack(fill=tk.X, pady=10)
