"""
Tkinter 상단 배너 카드 UI 레이아웃 빌더 모듈 (View)
내 PC 정보(호스트명, 대표 IPv4 주소) 강조 표시 및 원클릭 복사 버튼 위젯을 생성합니다.
"""
import tkinter as tk
from tkinter import ttk
from typing import Any


def build_top_banner_card(app: Any, parent: tk.Widget) -> tk.Frame:
    """
    상단 내 컴퓨터 정보 및 IP 강조 배너 카드를 생성합니다.

    Args:
        app: OneClickShareApp 애플리케이션 인스턴스
        parent: 부모 위젯

    Returns:
        생성된 top_card Frame 위젯
    """
    top_card = tk.Frame(parent, bg="#eff6ff", bd=1, relief=tk.SOLID, padx=12, pady=10)
    top_card.pack(fill=tk.X, padx=10, pady=(10, 5))

    top_left = tk.Frame(top_card, bg="#eff6ff")
    top_left.pack(side=tk.LEFT, fill=tk.Y)

    title_lbl = tk.Label(
        top_left,
        text="원클릭 사내 공유 매니저",
        font=("Malgun Gothic", 12, "bold"),
        bg="#eff6ff",
        fg="#1e3a8a"
    )
    title_lbl.pack(anchor="w")

    ip_info_frame = tk.Frame(top_left, bg="#eff6ff")
    ip_info_frame.pack(anchor="w", pady=(4, 0))

    lbl_ip_title = tk.Label(
        ip_info_frame,
        text="내 IP 주소:",
        font=("Malgun Gothic", 10, "bold"),
        bg="#eff6ff",
        fg="#1e40af"
    )
    lbl_ip_title.pack(side=tk.LEFT)

    lbl_ip_val = tk.Label(
        ip_info_frame,
        text=f" {app.local_ip} ",
        font=("Consolas", 12, "bold"),
        bg="#dbeafe",
        fg="#1e3a8a",
        relief=tk.RIDGE,
        bd=1
    )
    lbl_ip_val.pack(side=tk.LEFT, padx=(4, 8))

    lbl_host_val = tk.Label(
        ip_info_frame,
        text=f"(PC 이름: {app.hostname})",
        font=("Malgun Gothic", 9),
        bg="#eff6ff",
        fg="#64748b"
    )
    lbl_host_val.pack(side=tk.LEFT)

    # 우측 원클릭 복사 버튼 영역
    top_right = tk.Frame(top_card, bg="#eff6ff")
    top_right.pack(side=tk.RIGHT, fill=tk.Y)

    btn_copy_ip = tk.Button(
        top_right,
        text="IP 복사",
        font=("Malgun Gothic", 9, "bold"),
        bg="#2563eb",
        fg="white",
        activebackground="#1d4ed8",
        activeforeground="white",
        relief=tk.RAISED,
        padx=8,
        pady=3,
        cursor="hand2",
        command=app._action_copy_ip
    )
    btn_copy_ip.pack(side=tk.LEFT, padx=(0, 6))

    btn_copy_unc = tk.Button(
        top_right,
        text="접속경로 복사",
        font=("Malgun Gothic", 9, "bold"),
        bg="#0284c7",
        fg="white",
        activebackground="#0369a1",
        activeforeground="white",
        relief=tk.RAISED,
        padx=8,
        pady=3,
        cursor="hand2",
        command=app._action_copy_share_path
    )
    btn_copy_unc.pack(side=tk.LEFT)

    return top_card
