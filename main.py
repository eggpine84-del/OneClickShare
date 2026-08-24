"""
원클릭 사내 공유 매니저 메인 실행 엔트리포인트
프로그램 실행 시 관리자 권한을 자동으로 점검/승격하고 메인 GUI 애플리케이션을 구동합니다.
"""
import sys
import tkinter as tk
from shell.system_adapter import is_admin, run_as_admin
from shell.gui import OneClickShareApp


def main() -> None:
    """
    메인 실행 함수: 관리자 권한 확인 및 GUI 루프 실행
    """
    # 1. 관리자 권한 점검 (UAC 자동 승격)
    if not is_admin():
        run_as_admin()
        return

    # 2. Tkinter GUI 실행
    root = tk.Tk()
    app = OneClickShareApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
