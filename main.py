"""Điểm khởi động ứng dụng: chạy python main.py từ thư mục gốc."""

import sqlite3
from tkinter import messagebox

from ui import actions, data, interface


def main():
    """Tạo cửa sổ, chuẩn bị dữ liệu, rồi nhận thao tác của người dùng."""
    window = interface.build_interface()
    try:
        data.init_database()
    except sqlite3.Error as error:
        messagebox.showerror(
            "Không thể khởi tạo dữ liệu",
            data.database_error_message(error),
            parent=window,
        )
        window.destroy()
        return

    if not actions.lam_moi_du_lieu():
        window.destroy()
        return
    window.mainloop()


if __name__ == "__main__":
    main()
