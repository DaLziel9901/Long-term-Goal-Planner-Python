"""Ứng dụng lịch dài hạn: giao diện Tkinter và dự án lưu bằng SQLite.

Chạy trực tiếp file này. Việc import chỉ nạp hàm, không mở cửa sổ hay tạo DB.
"""

import re
import sqlite3
import tkinter as tk
import tkinter.font as tkfont
import unicodedata
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk


# Đường dẫn luôn cạnh source, kể cả khi chạy từ một thư mục Terminal khác.
DB_PATH = Path(__file__).resolve().with_name("calendar.db")
Sample = []  # Giữ tên biến cũ; được đồng bộ từ SQLite, không tự sinh dự án mẫu.

BG = "#F4F5F7"
WHITE = "#FFFFFF"
TEXT = "#273343"
MUTED = "#707B89"
BLUE = "#3869B8"
BLUE_HOVER = "#2B5598"
LIGHT_BLUE = "#EBF0F8"
BORDER = "#E1E5EB"
SOFT = "#F8F9FB"
MAU_TRANG_THAI = {"Chưa làm": "#8A6A36", "Đang làm": BLUE, "Hoàn thành": "#39806A"}
NEN_TRANG_THAI = {"Chưa làm": "#F7F3EA", "Đang làm": LIGHT_BLUE, "Hoàn thành": "#EAF4EF"}
TEN_THU = ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật")

window = None
add_dialog = None
active_nav_button = None
selected_project_id = None
task_dialog = None


# ---------------------------------------------------------------------------
# Tầng dữ liệu: không gọi widget Tkinter, có thể kiểm thử riêng hoặc dùng lại.
# ---------------------------------------------------------------------------
def connect_database():
    connection = sqlite3.connect(DB_PATH, timeout=3)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database():
    """Chỉ tạo bảng nếu chưa có; không ghi đè hoặc tự thêm dữ liệu mẫu."""
    # 'with connection' quản lý giao dịch, còn closing() thực sự đóng kết nối.
    with closing(connect_database()) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                start_date TEXT,
                end_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                planned_date TEXT,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'Chưa làm'
                    CHECK (status IN ('Chưa làm', 'Đang làm', 'Hoàn thành')),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS tasks_project_idx ON tasks(project_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS tasks_date_idx ON tasks(planned_date)")


def parse_input_date(value, field_name):
    """Đổi DD/MM/YYYY thành ISO để lưu; ô trống trở thành SQL NULL."""
    value = (value or "").strip()
    if not value:
        return None
    if not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", value):
        raise ValueError(f"{field_name} cần có định dạng DD/MM/YYYY, ví dụ 25/10/2026.")
    try:
        return datetime.strptime(value, "%d/%m/%Y").date().isoformat()
    except ValueError:
        raise ValueError(f"{field_name} không hợp lệ. Vui lòng kiểm tra lại ngày, tháng, năm.") from None


def name_key(name):
    """So sánh tên tiếng Việt, không phân biệt hoa/thường và dạng mã Unicode."""
    return unicodedata.normalize("NFC", name.strip()).casefold()


def add_project(name, description="", start_date="", end_date=""):
    """Kiểm tra và lưu dự án; chỉ trả ID sau khi giao dịch đã commit."""
    name = name.strip()
    if not name:
        raise ValueError("Vui lòng nhập tên dự án.")
    start = parse_input_date(start_date, "Ngày bắt đầu")
    end = parse_input_date(end_date, "Ngày kết thúc")
    if start and end and end < start:
        raise ValueError("Ngày kết thúc không được trước ngày bắt đầu.")

    with closing(connect_database()) as connection, connection:
        # Giữ kiểm tra trùng và INSERT trong cùng giao dịch để tránh lưu trùng
        # khi hai phiên bản ứng dụng cùng thêm dự án tại một thời điểm.
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute("SELECT name FROM projects").fetchall()
        if any(name_key(row["name"]) == name_key(name) for row in existing):
            raise ValueError("Tên dự án này đã tồn tại. Vui lòng chọn tên khác.")
        try:
            cursor = connection.execute(
                "INSERT INTO projects (name, description, start_date, end_date) VALUES (?, ?, ?, ?)",
                (name, (description or "").strip(), start, end),
            )
        except sqlite3.IntegrityError:
            raise ValueError("Tên dự án này đã tồn tại. Vui lòng chọn tên khác.") from None
        project_id = cursor.lastrowid
    return project_id


def load_projects():
    """Đọc dữ liệu mới nhất theo thứ tự tạo, không dựa vào danh sách mẫu."""
    with closing(connect_database()) as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM projects ORDER BY id")]


def get_project(exam):
    """Nhận ID dự án; vẫn hỗ trợ tên để tương thích show_sample('BTL Python')."""
    with closing(connect_database()) as connection:
        if isinstance(exam, int):
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (exam,)).fetchone()
        else:
            row = connection.execute("SELECT * FROM projects WHERE name = ?", (exam,)).fetchone()
        return dict(row) if row else None


def xoa_du_an(project_id):
    """Xóa dự án; khóa ngoại xóa các công việc đi kèm trong cùng giao dịch."""
    with closing(connect_database()) as connection, connection:
        cursor = connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        if cursor.rowcount == 0:
            raise ValueError("Dự án không còn tồn tại. Vui lòng tải lại danh sách.")


TRANG_THAI_CONG_VIEC = ("Chưa làm", "Đang làm", "Hoàn thành")


def kiem_tra_cong_viec(name, description, planned_date, due_date, status):
    """Kiểm tra dữ liệu trước khi thêm hoặc sửa; trả ngày theo định dạng SQLite."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Vui lòng nhập tên công việc.")
    planned = parse_input_date(planned_date, "Ngày thực hiện")
    due = parse_input_date(due_date, "Hạn hoàn thành")
    if planned and due and due < planned:
        raise ValueError("Hạn hoàn thành không được trước ngày thực hiện.")
    if status not in TRANG_THAI_CONG_VIEC:
        raise ValueError("Vui lòng chọn trạng thái công việc hợp lệ.")
    return name, (description or "").strip(), planned, due, status


def them_cong_viec(project_id, name, description="", planned_date="", due_date="", status="Chưa làm"):
    """Lưu công việc vào một dự án có thật và trả về mã vừa tạo."""
    values = kiem_tra_cong_viec(name, description, planned_date, due_date, status)
    with closing(connect_database()) as connection, connection:
        if connection.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone() is None:
            raise ValueError("Dự án không còn tồn tại. Vui lòng tải lại danh sách.")
        cursor = connection.execute(
            """INSERT INTO tasks (project_id, name, description, planned_date, due_date, status)
               VALUES (?, ?, ?, ?, ?, ?)""", (project_id, *values)
        )
        task_id = cursor.lastrowid
    return task_id


def sua_cong_viec(task_id, name, description="", planned_date="", due_date="", status="Chưa làm"):
    """Cập nhật nội dung công việc, giữ nguyên dự án đã gắn khi tạo."""
    values = kiem_tra_cong_viec(name, description, planned_date, due_date, status)
    with closing(connect_database()) as connection, connection:
        cursor = connection.execute(
            """UPDATE tasks SET name = ?, description = ?, planned_date = ?, due_date = ?, status = ?
               WHERE id = ?""", (*values, task_id)
        )
        if cursor.rowcount == 0:
            raise ValueError("Công việc không còn tồn tại. Vui lòng tải lại danh sách.")


def xoa_cong_viec(task_id):
    with closing(connect_database()) as connection, connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cursor.rowcount == 0:
            raise ValueError("Công việc không còn tồn tại. Vui lòng tải lại danh sách.")


def doi_trang_thai(task_id, status):
    """Đổi trạng thái trực tiếp từ danh sách hoặc lịch tuần."""
    if status not in TRANG_THAI_CONG_VIEC:
        raise ValueError("Vui lòng chọn trạng thái công việc hợp lệ.")
    with closing(connect_database()) as connection, connection:
        cursor = connection.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        if cursor.rowcount == 0:
            raise ValueError("Công việc không còn tồn tại. Vui lòng tải lại danh sách.")


def lay_cong_viec(task_id):
    with closing(connect_database()) as connection:
        row = connection.execute(
            """SELECT tasks.*, projects.name AS project_name FROM tasks
               JOIN projects ON projects.id = tasks.project_id WHERE tasks.id = ?""", (task_id,)
        ).fetchone()
        return dict(row) if row else None


def danh_sach_cong_viec(project_id=None):
    """Ngày thực hiện tăng dần; công việc chưa lên lịch đặt cuối danh sách."""
    query = """SELECT tasks.*, projects.name AS project_name FROM tasks
               JOIN projects ON projects.id = tasks.project_id"""
    parameters = ()
    if project_id is not None:
        query += " WHERE tasks.project_id = ?"
        parameters = (project_id,)
    query += " ORDER BY tasks.planned_date IS NULL, tasks.planned_date, tasks.id"
    with closing(connect_database()) as connection:
        return [dict(row) for row in connection.execute(query, parameters)]


def cong_viec_trong_tuan(ngay_dau_tuan):
    """Lấy bảy ngày từ ngày bắt đầu; công việc chưa lên lịch không nằm trên lịch."""
    from datetime import timedelta

    ngay_cuoi_tuan = ngay_dau_tuan + timedelta(days=6)
    with closing(connect_database()) as connection:
        rows = connection.execute(
            """SELECT tasks.*, projects.name AS project_name FROM tasks
               JOIN projects ON projects.id = tasks.project_id
               WHERE tasks.planned_date BETWEEN ? AND ?
               ORDER BY tasks.planned_date, tasks.id""",
            (ngay_dau_tuan.isoformat(), ngay_cuoi_tuan.isoformat()),
        )
        return [dict(row) for row in rows]


def thong_ke_du_an():
    """Mỗi dự án có tổng việc, ba trạng thái và phần trăm hoàn thành."""
    with closing(connect_database()) as connection:
        rows = connection.execute("""
            SELECT projects.id, projects.name, COUNT(tasks.id) AS total,
                   SUM(CASE WHEN tasks.status = 'Hoàn thành' THEN 1 ELSE 0 END) AS done,
                   SUM(CASE WHEN tasks.status = 'Chưa làm' THEN 1 ELSE 0 END) AS todo,
                   SUM(CASE WHEN tasks.status = 'Đang làm' THEN 1 ELSE 0 END) AS doing
            FROM projects LEFT JOIN tasks ON projects.id = tasks.project_id
            GROUP BY projects.id ORDER BY projects.id
        """)
        result = []
        for row in rows:
            project = dict(row)
            project["pending"] = project["todo"] + project["doing"]
            project["progress"] = round(project["done"] * 100 / project["total"], 1) if project["total"] else 0
            result.append(project)
        return result


def thong_ke_tong_quan(today=None):
    """Quá hạn: việc chưa xong có hạn hoàn thành trước ngày đang xét."""
    from datetime import date

    today = today or date.today()
    with closing(connect_database()) as connection:
        row = connection.execute("""
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(status = 'Hoàn thành'), 0) AS done,
                   COALESCE(SUM(status = 'Chưa làm'), 0) AS todo,
                   COALESCE(SUM(status = 'Đang làm'), 0) AS doing,
                   COALESCE(SUM(status != 'Hoàn thành'
                       AND due_date < ?), 0) AS overdue
            FROM tasks
        """, (today.isoformat(),)).fetchone()
        result = dict(row)
        result["projects"] = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    result["pending"] = result["todo"] + result["doing"]
    result["progress"] = round(result["done"] * 100 / result["total"], 1) if result["total"] else 0
    return result


def display_date(value):
    if not value:
        return "Chưa đặt ngày"
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return "Ngày cần cập nhật"


def database_error_message(error):
    """Chuyển lỗi kỹ thuật thành hướng dẫn tiếng Việt, không báo lưu giả."""
    code = getattr(error, "sqlite_errorcode", None)
    if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
        return "Dữ liệu đang được chương trình khác sử dụng. Hãy thử lại sau ít giây."
    if code in (sqlite3.SQLITE_READONLY, sqlite3.SQLITE_CANTOPEN):
        return "Không thể mở hoặc ghi calendar.db. Hãy kiểm tra quyền ghi của thư mục ứng dụng."
    return "Không thể truy cập dữ liệu dự án. Hãy kiểm tra file calendar.db và dung lượng ổ đĩa rồi thử lại."


# ---------------------------------------------------------------------------
# Các hàm giao diện: giữ nguyên các tên hàm và khung từ phiên bản ban đầu.
# ---------------------------------------------------------------------------
def make_label(parent, text="", size=10, color=TEXT, bold=False, bg=WHITE, **options):
    return tk.Label(parent, text=text, bg=bg, fg=color, anchor="w", justify="left",
                    font=("Segoe UI", size, "bold" if bold else "normal"), **options)


def make_button(parent, text, command, primary=False):
    """Nút dùng chung có màu khi rê chuột, luôn gắn hành động thực tế."""
    base = BLUE if primary else WHITE
    hover = BLUE_HOVER if primary else LIGHT_BLUE
    button = tk.Button(parent, text=text, command=command, bg=base,
                       fg=WHITE if primary else TEXT, activebackground=hover,
                       activeforeground=WHITE if primary else BLUE,
                       relief="flat", bd=0, cursor="hand2", padx=16, pady=11,
                       font=("Segoe UI", 10, "bold"), takefocus=True)
    button.bind("<Enter>", lambda event: button.configure(bg=hover))
    button.bind("<Leave>", lambda event: button.configure(bg=base))
    return button


def show_empty_project():
    global selected_project_id
    selected_project_id = None
    content_title.set("Chưa có dự án")
    content_description.set("Thêm một dự án ở bên trái để bắt đầu.")
    start_text.set("Chưa đặt ngày")
    end_text.set("Chưa đặt ngày")
    project_badge.set("")
    cap_nhat_cong_viec([])
    content_canvas.yview_moveto(0)


def show_sample(exam):
    """Đọc dự án từ SQLite rồi cập nhật widget có sẵn, không tạo thêm cửa sổ."""
    global selected_project_id
    try:
        project = get_project(exam)
        tasks = danh_sach_cong_viec(project["id"]) if project else []
    except sqlite3.Error as error:
        # Đọc thất bại thì giữ cả tiêu đề lẫn công việc của dự án trước đó.
        previous = str(selected_project_id)
        if selected_project_id is not None and project_list.exists(previous):
            if project_list.selection() != (previous,):
                project_list.selection_set(previous)
        elif project_list.selection():
            project_list.selection_remove(*project_list.selection())
        messagebox.showerror("Không thể đọc dự án", database_error_message(error), parent=window)
        return False
    if project is None:
        show_empty_project()
        return True
    selected_project_id = project["id"]
    content_title.set(project["name"])
    content_description.set(project["description"] or "Dự án này chưa có mô tả.")
    start_text.set(display_date(project["start_date"]))
    end_text.set(display_date(project["end_date"]))
    cap_nhat_cong_viec(tasks)
    item_id = str(project["id"])
    if project_list.exists(item_id):
        # Không gọi selection_set lặp lại để tránh vòng lặp TreeviewSelect.
        if project_list.selection() != (item_id,):
            project_list.selection_set(item_id)
        project_list.focus(item_id)
        project_list.see(item_id)
    content_canvas.yview_moveto(0)
    return True


def select_project(event=None):
    selected = project_list.selection()
    if selected and int(selected[0]) != selected_project_id:
        show_sample(int(selected[0]))


def refresh_project_list(select_id=None):
    """Đọc DB trước khi thay danh sách; dùng ID ổn định làm iid của Treeview."""
    try:
        projects = load_projects()
    except sqlite3.Error as error:
        messagebox.showerror("Không thể tải dự án", database_error_message(error), parent=window)
        return False

    target = select_id if select_id is not None else selected_project_id
    Sample[:] = [project["name"] for project in projects]
    items = project_list.get_children()
    if items:
        project_list.delete(*items)
    for project in projects:
        project_list.insert("", "end", iid=str(project["id"]), text=project["name"])
    # Tên dài vẫn đọc được bằng thanh cuộn ngang, không đẩy rộng sidebar.
    font = tkfont.Font(family="Segoe UI", size=11)
    column_width = max([210] + [font.measure(name) + 30 for name in Sample])
    project_list.column("#0", width=column_width, minwidth=210, stretch=False)
    project_count.set(str(len(projects)))
    if projects:
        ids = {project["id"] for project in projects}
        return show_sample(target if target in ids else projects[0]["id"])
    else:
        show_empty_project()
    return True


def xoa_du_an_dang_chon():
    """Hỏi xác nhận trước khi xóa; chỉ đổi giao diện sau khi commit thành công."""
    project_id = selected_project_id
    if project_id is None:
        messagebox.showinfo("Chọn dự án", "Bạn hãy chọn dự án cần xóa ở danh sách bên trái.", parent=window)
        return
    try:
        project = get_project(project_id)
        if project is None:
            raise ValueError("Dự án không còn tồn tại. Vui lòng tải lại danh sách.")
        count = len(danh_sach_cong_viec(project_id))
    except (sqlite3.Error, ValueError) as error:
        text = database_error_message(error) if isinstance(error, sqlite3.Error) else str(error)
        messagebox.showerror("Không thể đọc dự án", text, parent=window)
        return
    name = project["name"]
    if len(name) > 160:
        name = name[:159] + "…"
    detail = f"Toàn bộ {count} công việc thuộc dự án cũng sẽ bị xóa." if count else "Dự án này chưa có công việc."
    confirmed = messagebox.askyesno(
        "Xóa dự án", f"Xóa dự án “{name}”?\n\n{detail}\nThao tác này không thể hoàn tác.",
        parent=window, default=messagebox.NO,
    )
    if not confirmed:
        return
    try:
        xoa_du_an(project_id)
    except (sqlite3.Error, ValueError) as error:
        text = database_error_message(error) if isinstance(error, sqlite3.Error) else str(error)
        messagebox.showerror("Chưa xóa được dự án", text, parent=window)
        return
    if lam_moi_du_lieu():
        status_text.set("Đã xóa dự án và các công việc thuộc dự án.")
    else:
        status_text.set("Đã xóa dự án, chưa tải lại được đầy đủ dữ liệu.")


def open_add_project():
    """Chỉ mở một Toplevel; Lưu kiểm tra dữ liệu rồi commit trước khi refresh."""
    global add_dialog
    if add_dialog is not None and add_dialog.winfo_exists():
        add_dialog.lift()
        add_dialog.focus_set()
        return add_dialog

    dialog = tk.Toplevel(window)
    add_dialog = dialog
    dialog.withdraw()
    dialog.title("Thêm dự án mới")
    dialog.configure(bg=WHITE)
    dialog.resizable(False, False)
    dialog.transient(window)

    def close_dialog(event=None):
        global add_dialog
        dialog.grab_release()
        dialog.destroy()
        add_dialog = None
        button_add.focus_set()

    dialog.protocol("WM_DELETE_WINDOW", close_dialog)
    dialog.bind("<Escape>", close_dialog)
    header = tk.Frame(dialog, bg=LIGHT_BLUE, padx=28, pady=20)
    header.pack(fill="x")
    make_label(header, "Thêm dự án", 19, TEXT, True, LIGHT_BLUE).pack(anchor="w")

    form = tk.Frame(dialog, bg=WHITE, padx=28, pady=20)
    form.pack(fill="both", expand=True)
    make_label(form, "Tên dự án *", bold=True).pack(anchor="w", pady=(0, 7))
    name_entry = ttk.Entry(form, style="Form.TEntry")
    name_entry.pack(fill="x")
    make_label(form, "Mô tả", bold=True).pack(anchor="w", pady=(18, 7))
    description_box = tk.Frame(form, bg=BORDER, padx=1, pady=1)
    description_box.pack(fill="x")
    description_text = tk.Text(description_box, height=4, width=48, wrap="word", relief="flat",
                               bg=SOFT, fg=TEXT, font=("Segoe UI", 10), padx=10, pady=9,
                               insertbackground=BLUE, undo=True)
    description_scroll = ttk.Scrollbar(description_box, command=description_text.yview,
                                       style="Slim.Vertical.TScrollbar")
    description_text.configure(yscrollcommand=description_scroll.set)
    description_scroll.pack(side="right", fill="y")
    description_text.pack(side="left", fill="both", expand=True)

    dates = tk.Frame(form, bg=WHITE)
    dates.pack(fill="x", pady=(18, 0))
    dates.columnconfigure((0, 1), weight=1, uniform="dates")
    make_label(dates, "Ngày bắt đầu", bold=True).grid(row=0, column=0, sticky="w", pady=(0, 7))
    make_label(dates, "Ngày kết thúc", bold=True).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 7))
    start_entry = ttk.Entry(dates, width=20, style="Form.TEntry")
    end_entry = ttk.Entry(dates, width=20, style="Form.TEntry")
    start_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6))
    end_entry.grid(row=1, column=1, sticky="ew", padx=(12, 0))
    make_label(form, "DD/MM/YYYY · Có thể để trống ngày và mô tả", 9, MUTED).pack(anchor="w", pady=(8, 0))

    def save_project(event=None):
        try:
            project_id = add_project(name_entry.get(), description_text.get("1.0", "end-1c"),
                                     start_entry.get(), end_entry.get())
        except ValueError as error:
            messagebox.showwarning("Kiểm tra thông tin", str(error), parent=dialog)
            return "break"
        except sqlite3.Error as error:
            messagebox.showerror("Chưa lưu được dự án", database_error_message(error), parent=dialog)
            return "break"
        # add_project chỉ trả về sau commit: không cập nhật giao diện khi INSERT lỗi.
        close_dialog()
        if refresh_project_list(select_id=project_id):
            status_text.set("Đã thêm dự án.")
        else:
            status_text.set("Đã lưu dự án, chưa tải lại được danh sách.")
        return "break"

    footer = tk.Frame(dialog, bg=SOFT, padx=28, pady=16)
    footer.pack(fill="x")
    save_button = make_button(footer, "Lưu dự án", save_project, primary=True)
    save_button.pack(side="right")
    make_button(footer, "Hủy", close_dialog).pack(side="right", padx=(0, 10))
    name_entry.bind("<Return>", save_project)

    # Đặt tên widget để có thể kiểm thử thao tác mà không phụ thuộc tọa độ màn hình.
    dialog.name_entry = name_entry
    dialog.description_text = description_text
    dialog.start_entry = start_entry
    dialog.end_entry = end_entry
    dialog.save_button = save_button
    dialog.save_project = save_project
    dialog.close_dialog = close_dialog
    dialog.update_idletasks()
    width = max(540, dialog.winfo_reqwidth())
    height = dialog.winfo_reqheight()
    x = window.winfo_rootx() + (window.winfo_width() - width) // 2
    y = window.winfo_rooty() + (window.winfo_height() - height) // 2
    x = max(0, min(x, dialog.winfo_screenwidth() - width))
    y = max(0, min(y, dialog.winfo_screenheight() - height - 60))
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    dialog.deiconify()
    dialog.wait_visibility()
    dialog.grab_set()
    name_entry.focus_set()
    return dialog


def show_project():
    """Giữ hàm nhập dự án của bản cũ; chuyển việc nhập sang hộp thoại đầy đủ."""
    return open_add_project()


def resize_content(event):
    """Giữ nội dung vừa chiều ngang; chiều dọc có thanh cuộn khi văn bản dài."""
    content_canvas.itemconfigure(content_window, width=event.width)
    width = max(120, event.width - 56)
    for label in (project_heading, description_label, empty_label):
        label.configure(wraplength=width)


def scroll_content(event):
    # Bảng công việc và ô ghi chú tự xử lý cuộn của riêng chúng.
    if isinstance(event.widget, (ttk.Treeview, tk.Text, ttk.Combobox)):
        return None
    widget = event.widget
    while widget is not None:
        if widget in (content_canvas, stats_canvas):
            bounds = widget.bbox("all")
            if bounds and bounds[3] > widget.winfo_height():
                direction = -1 if event.delta > 0 else 1
                widget.yview_scroll(direction * max(1, abs(event.delta) // 120), "units")
                return "break"
            return None
        widget = getattr(widget, "master", None)


def set_active_frame(frame, active_button):
    global active_nav_button
    for page in (under_frame_1, under_frame_2, under_frame_3):
        page.pack_forget()
    frame.pack(fill="both", expand=True, padx=28, pady=(0, 12))
    active_nav_button = active_button
    for button in (button1, button2, button3):
        selected = button is active_button
        button.configure(bg=LIGHT_BLUE if selected else WHITE, fg=BLUE if selected else MUTED)
    headings = {
        button1: ("Kế hoạch", "Dự án và công việc của bạn"),
        button2: ("Thống kê", "Tiến độ và trạng thái công việc"),
        button3: ("Lịch tuần", "Sắp xếp theo ngày dự kiến thực hiện"),
    }
    page_title.set(headings[active_button][0])
    page_subtitle.set(headings[active_button][1])


def show_frame1():
    set_active_frame(under_frame_1, button1)


def show_frame2():
    cap_nhat_thong_ke()
    set_active_frame(under_frame_2, button2)


def show_frame3():
    cap_nhat_lich_tuan()
    set_active_frame(under_frame_3, button3)


def tao_bang(parent, columns, height=6, expand=True):
    """Bảng có thanh cuộn; mỗi cột gồm tên trong code, nhãn và chiều rộng."""
    frame = tk.Frame(parent, bg=WHITE)
    frame.pack(fill="both" if expand else "x", expand=expand)
    tree = ttk.Treeview(frame, columns=[column[0] for column in columns],
                       show="headings", selectmode="browse", height=height, style="Task.Treeview")
    for index, (key, label, width) in enumerate(columns):
        tree.heading(key, text=label, anchor="w")
        tree.column(key, width=width, minwidth=70, stretch=index == 0)
    vertical = ttk.Scrollbar(frame, command=tree.yview, style="Slim.Vertical.TScrollbar")
    horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview,
                               style="Slim.Horizontal.TScrollbar")
    tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    for status, color in MAU_TRANG_THAI.items():
        tree.tag_configure(status, foreground=color)
    return tree


def cap_nhat_cong_viec(tasks=None):
    """Nạp công việc của dự án đang chọn và tính tiến độ thực tế."""
    if tasks is None:
        try:
            tasks = danh_sach_cong_viec(selected_project_id) if selected_project_id else []
        except sqlite3.Error as error:
            messagebox.showerror("Không thể đọc công việc", database_error_message(error), parent=window)
            return False
    selection = task_list.selection()
    items = task_list.get_children()
    if items:
        task_list.delete(*items)
    for task in tasks:
        task_list.insert("", "end", iid=str(task["id"]), tags=(task["status"],), values=(
            task["name"], display_date(task["planned_date"]), display_date(task["due_date"]), task["status"]))
    if selection and task_list.exists(selection[0]):
        task_list.selection_set(selection[0])
    done = sum(task["status"] == "Hoàn thành" for task in tasks)
    progress = round(done * 100 / len(tasks), 1) if tasks else 0
    project_progress.configure(value=progress)
    project_progress_text.set(f"{done}/{len(tasks)} công việc hoàn thành · {progress:g}%")
    project_badge.set(f"{len(tasks)} công việc")
    if tasks:
        empty_label.pack_forget()
    else:
        empty_label.configure(text="Chưa có công việc. Nhấn “+ Công việc” để thêm.")
        empty_label.pack(fill="x", pady=(0, 6), before=task_list.master)
    return True


def lam_moi_du_lieu(project_id=None):
    """Sau mỗi lần lưu, ba trang cùng đọc lại một nguồn dữ liệu SQLite."""
    result = refresh_project_list(select_id=project_id)
    result = cap_nhat_thong_ke() and result
    result = cap_nhat_lich_tuan() and result
    return result


def chon_cong_viec(tree):
    selected = tree.selection()
    if not selected:
        messagebox.showinfo("Chọn công việc", "Bạn hãy chọn một công việc trong danh sách.", parent=window)
        return None
    return int(selected[0])


def sua_viec_da_chon(tree):
    task_id = chon_cong_viec(tree)
    if task_id is not None:
        mo_form_cong_viec(task_id=task_id)


def xoa_viec_da_chon(tree):
    task_id = chon_cong_viec(tree)
    if task_id is None or not messagebox.askyesno("Xóa công việc", "Xóa công việc đã chọn?", parent=window):
        return
    try:
        xoa_cong_viec(task_id)
    except (sqlite3.Error, ValueError) as error:
        text = database_error_message(error) if isinstance(error, sqlite3.Error) else str(error)
        messagebox.showerror("Chưa xóa được công việc", text, parent=window)
        return
    lam_moi_du_lieu()
    status_text.set("Đã xóa công việc.")


def danh_dau_hoan_thanh(tree):
    task_id = chon_cong_viec(tree)
    if task_id is None:
        return
    try:
        doi_trang_thai(task_id, "Hoàn thành")
    except (sqlite3.Error, ValueError) as error:
        text = database_error_message(error) if isinstance(error, sqlite3.Error) else str(error)
        messagebox.showerror("Chưa cập nhật được", text, parent=window)
        return
    lam_moi_du_lieu()
    status_text.set("Đã đánh dấu hoàn thành.")


def mo_form_cong_viec(task_id=None, project_id=None, planned_date=None):
    """Một form dùng cho thêm và sửa công việc, không tạo thêm cửa sổ Tk."""
    global task_dialog
    if task_dialog is not None and task_dialog.winfo_exists():
        task_dialog.lift()
        task_dialog.focus_set()
        return task_dialog
    try:
        projects = load_projects()
        task = lay_cong_viec(task_id) if task_id is not None else None
    except sqlite3.Error as error:
        messagebox.showerror("Không thể đọc dữ liệu", database_error_message(error), parent=window)
        return None
    if not projects:
        messagebox.showinfo("Chưa có dự án", "Hãy thêm một dự án trước khi tạo công việc.", parent=window)
        return None
    if task_id is not None and task is None:
        messagebox.showinfo("Không tìm thấy", "Công việc này không còn tồn tại.", parent=window)
        return None

    dialog = tk.Toplevel(window)
    task_dialog = dialog
    dialog.withdraw()
    dialog.title("Sửa công việc" if task else "Thêm công việc")
    dialog.configure(bg=WHITE)
    dialog.transient(window)
    dialog.resizable(False, False)

    def dong_form(event=None):
        global task_dialog
        dialog.grab_release()
        dialog.destroy()
        task_dialog = None
        window.focus_set()

    dialog.protocol("WM_DELETE_WINDOW", dong_form)
    dialog.bind("<Escape>", dong_form)
    form = tk.Frame(dialog, bg=WHITE, padx=24, pady=22)
    form.pack(fill="both", expand=True)
    make_label(form, "Sửa công việc" if task else "Thêm công việc", 19, bold=True).pack(anchor="w", pady=(0, 18))
    make_label(form, "Dự án", bold=True).pack(anchor="w", pady=(0, 6))
    project_combo = ttk.Combobox(form, values=[project["name"] for project in projects],
                                 state="readonly", style="Form.TCombobox", width=48)
    default_project = task["project_id"] if task else (project_id or selected_project_id)
    index = next((i for i, project in enumerate(projects) if project["id"] == default_project), 0)
    project_combo.current(index)
    if task:
        project_combo.configure(state="disabled")
    project_combo.pack(fill="x")
    make_label(form, "Tên công việc *", bold=True).pack(anchor="w", pady=(14, 6))
    name_entry = ttk.Entry(form, style="Form.TEntry")
    name_entry.pack(fill="x")
    make_label(form, "Ghi chú", bold=True).pack(anchor="w", pady=(14, 6))
    text_frame = tk.Frame(form, bg=BORDER, padx=1, pady=1)
    text_frame.pack(fill="x")
    description_text = tk.Text(text_frame, height=3, width=48, wrap="word", font=("Segoe UI", 10),
                               bg=SOFT, fg=TEXT, relief="flat", padx=9, pady=8, undo=True)
    scrollbar = ttk.Scrollbar(text_frame, command=description_text.yview, style="Slim.Vertical.TScrollbar")
    description_text.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    description_text.pack(side="left", fill="both", expand=True)
    dates = tk.Frame(form, bg=WHITE)
    dates.pack(fill="x", pady=(14, 0))
    dates.columnconfigure((0, 1), weight=1, uniform="dates")
    make_label(dates, "Ngày dự kiến").grid(row=0, column=0, sticky="w", pady=(0, 6))
    make_label(dates, "Hạn hoàn thành").grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 6))
    start_entry = ttk.Entry(dates, width=20, style="Form.TEntry")
    end_entry = ttk.Entry(dates, width=20, style="Form.TEntry")
    start_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6))
    end_entry.grid(row=1, column=1, sticky="ew", padx=(12, 0))
    make_label(form, "DD/MM/YYYY · Để trống nếu chưa xếp lịch", 9, MUTED).pack(anchor="w", pady=(7, 14))
    make_label(form, "Trạng thái", bold=True).pack(anchor="w", pady=(0, 6))
    status_combo = ttk.Combobox(form, values=TRANG_THAI_CONG_VIEC, state="readonly", style="Form.TCombobox")
    status_combo.set(task["status"] if task else "Chưa làm")
    status_combo.pack(fill="x")
    if task:
        name_entry.insert(0, task["name"])
        description_text.insert("1.0", task["description"] or "")
        start_entry.insert(0, display_date(task["planned_date"]) if task["planned_date"] else "")
        end_entry.insert(0, display_date(task["due_date"]) if task["due_date"] else "")
    elif planned_date:
        start_entry.insert(0, planned_date.strftime("%d/%m/%Y"))

    def luu_viec(event=None):
        global week_start, selected_day
        chosen_project = projects[project_combo.current()]["id"]
        values = (name_entry.get(), description_text.get("1.0", "end-1c"),
                  start_entry.get(), end_entry.get(), status_combo.get())
        try:
            if task:
                sua_cong_viec(task_id, *values)
                saved_id = task_id
            else:
                saved_id = them_cong_viec(chosen_project, *values)
        except ValueError as error:
            messagebox.showwarning("Kiểm tra thông tin", str(error), parent=dialog)
            return "break"
        except sqlite3.Error as error:
            messagebox.showerror("Chưa lưu được công việc", database_error_message(error), parent=dialog)
            return "break"
        # Giá trị ngày ở đây đã được tầng dữ liệu kiểm tra hợp lệ và commit.
        if active_nav_button is button3 and start_entry.get().strip():
            selected_day = datetime.strptime(start_entry.get().strip(), "%d/%m/%Y").date()
            week_start = selected_day - timedelta(days=selected_day.weekday())
        dong_form()
        if lam_moi_du_lieu(chosen_project):
            status_text.set("Đã lưu công việc.")
        else:
            status_text.set("Đã lưu công việc, chưa tải lại được đầy đủ dữ liệu.")
        for tree in (task_list, day_task_list):
            if tree.exists(str(saved_id)):
                tree.selection_set(str(saved_id))
                tree.see(str(saved_id))
        return "break"

    footer = tk.Frame(dialog, bg=SOFT, padx=24, pady=14)
    footer.pack(fill="x")
    save_button = make_button(footer, "Lưu công việc", luu_viec, primary=True)
    save_button.pack(side="right")
    make_button(footer, "Hủy", dong_form).pack(side="right", padx=(0, 10))
    name_entry.bind("<Return>", luu_viec)
    dialog.name_entry = name_entry
    dialog.description_text = description_text
    dialog.start_entry = start_entry
    dialog.end_entry = end_entry
    dialog.status_combo = status_combo
    dialog.project_combo = project_combo
    dialog.save_button = save_button
    dialog.close_dialog = dong_form
    dialog.update_idletasks()
    width, height = max(540, dialog.winfo_reqwidth()), dialog.winfo_reqheight()
    x = max(0, window.winfo_rootx() + (window.winfo_width() - width) // 2)
    y = max(0, window.winfo_rooty() + (window.winfo_height() - height) // 2)
    x = max(0, min(x, dialog.winfo_screenwidth() - width))
    y = max(0, min(y, dialog.winfo_screenheight() - height - 60))
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    dialog.deiconify()
    dialog.wait_visibility()
    dialog.grab_set()
    name_entry.focus_set()
    return dialog


def tao_trang_thong_ke():
    global stats_values, stats_progress, stats_rows, stats_canvas, stats_status_values, stats_status_bars
    stats_values, stats_progress = {}, {}
    numbers = tk.Frame(under_frame_2, bg=BG)
    numbers.pack(fill="x", pady=(0, 16))
    for column, (key, caption) in enumerate((("projects", "Dự án"), ("total", "Công việc"),
                                           ("done", "Hoàn thành"), ("pending", "Chưa xong"),
                                           ("progress", "Tỷ lệ hoàn thành"))):
        numbers.columnconfigure(column, weight=1, uniform="numbers")
        card = tk.Frame(numbers, bg=WHITE, highlightbackground=BORDER, highlightthickness=1,
                        padx=16, pady=14)
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 10) if column < 4 else 0)
        make_label(card, caption, 10, MUTED).pack(anchor="w")
        stats_values[key] = tk.StringVar(window, "0%" if key == "progress" else "0")
        make_label(card, size=25, color=BLUE if key == "progress" else TEXT,
                   bold=True, textvariable=stats_values[key]).pack(anchor="w", pady=(8, 0))

    bottom = tk.Frame(under_frame_2, bg=BG)
    bottom.pack(fill="both", expand=True)
    left = tk.Frame(bottom, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    left.pack(side="left", fill="both", expand=True, padx=(0, 16))
    make_label(left, "Tiến độ theo dự án", 13, bold=True).pack(anchor="w", padx=20, pady=18)
    stats_canvas = tk.Canvas(left, bg=WHITE, highlightthickness=0, yscrollincrement=20)
    scroll = ttk.Scrollbar(left, command=stats_canvas.yview, style="Slim.Vertical.TScrollbar")
    stats_canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    stats_canvas.pack(fill="both", expand=True)
    stats_rows = tk.Frame(stats_canvas, bg=WHITE, padx=20)
    item = stats_canvas.create_window((0, 0), window=stats_rows, anchor="nw")
    stats_rows.bind("<Configure>", lambda event: stats_canvas.configure(scrollregion=stats_canvas.bbox("all")))
    stats_canvas.bind("<Configure>", lambda event: stats_canvas.itemconfigure(item, width=event.width))

    right = tk.Frame(bottom, bg=WHITE, width=254, highlightbackground=BORDER, highlightthickness=1)
    right.pack(side="right", fill="y")
    right.pack_propagate(False)
    make_label(right, "Trạng thái công việc", 12, bold=True).pack(anchor="w", padx=20, pady=12)
    stats_status_values, stats_status_bars = {}, {}
    for key, caption in (("todo", "Chưa làm"), ("doing", "Đang làm"), ("done", "Hoàn thành")):
        row = tk.Frame(right, bg=WHITE)
        row.pack(fill="x", padx=20, pady=(0, 3))
        make_label(row, caption, color=MAU_TRANG_THAI[caption]).pack(side="left")
        stats_status_values[key] = tk.StringVar(window, "0")
        make_label(row, textvariable=stats_status_values[key], bold=True).pack(side="right")
        bar = ttk.Progressbar(right, maximum=100, style=f"{key}.Horizontal.TProgressbar")
        bar.pack(fill="x", padx=20, pady=(0, 8))
        stats_status_bars[key] = bar
    tk.Frame(right, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(0, 8))
    late = tk.Frame(right, bg=WHITE)
    late.pack(fill="x", padx=20)
    make_label(late, "Quá hạn", color="#A6524C").pack(side="left")
    stats_status_values["overdue"] = tk.StringVar(window, "0")
    make_label(late, color="#A6524C", bold=True, textvariable=stats_status_values["overdue"]).pack(side="right")


def cap_nhat_thong_ke():
    global stats_progress
    try:
        summary = thong_ke_tong_quan()
        projects = thong_ke_du_an()
    except sqlite3.Error as error:
        messagebox.showerror("Không thể tải thống kê", database_error_message(error), parent=window)
        return False
    for key, variable in stats_values.items():
        variable.set(f"{summary[key]:g}%" if key == "progress" else str(summary[key]))
    for key, variable in stats_status_values.items():
        variable.set(str(summary[key]))
        if key in stats_status_bars:
            stats_status_bars[key].configure(value=summary[key] * 100 / summary["total"] if summary["total"] else 0)
    position = stats_canvas.yview()[0]
    for widget in stats_rows.winfo_children():
        widget.destroy()
    stats_progress = {}
    if not projects:
        make_label(stats_rows, "Chưa có dự án để thống kê.", color=MUTED).pack(anchor="w", pady=12)
    for project in projects:
        row = tk.Frame(stats_rows, bg=WHITE)
        row.pack(fill="x", pady=(2, 18))
        heading = tk.Frame(row, bg=WHITE)
        heading.pack(fill="x", pady=(0, 10))
        heading.columnconfigure(0, weight=1)
        label = make_label(heading, project["name"], 11, bold=True)
        label.grid(row=0, column=0, sticky="w")
        heading.bind("<Configure>", lambda event, text=label: text.configure(wraplength=max(80, event.width - 145)))
        make_label(heading, f"{project['done']}/{project['total']} · {project['progress']:g}%", 10, MUTED).grid(
            row=0, column=1, sticky="e", padx=(12, 0))
        bar = ttk.Progressbar(row, maximum=100, value=project["progress"], style="doing.Horizontal.TProgressbar")
        bar.pack(fill="x")
        stats_progress[project["id"]] = bar
        make_label(row, f"{project['pending']} công việc chưa xong", 9, MUTED).pack(anchor="w", pady=(6, 0))
    stats_canvas.update_idletasks()
    stats_canvas.yview_moveto(position)
    return True


def tao_trang_lich():
    global week_start, selected_day, week_title, week_columns, week_tasks_by_day
    global week_board, day_task_list, day_title, day_summary
    global week_card_limit
    selected_day = date.today()
    week_start = selected_day - timedelta(days=selected_day.weekday())
    week_columns, week_tasks_by_day = {}, {}
    week_card_limit = 2
    week_title = tk.StringVar(window)
    toolbar = tk.Frame(under_frame_3, bg=BG)
    toolbar.pack(fill="x", pady=(0, 12))
    make_label(toolbar, size=14, bold=True, bg=BG, textvariable=week_title).pack(side="left")
    next_button = make_button(toolbar, "Tuần sau ›", lambda: chuyen_tuan(1))
    today_button = make_button(toolbar, "Hôm nay", ve_tuan_hien_tai)
    prev_button = make_button(toolbar, "‹ Tuần trước", lambda: chuyen_tuan(-1))
    for button in (next_button, today_button, prev_button):
        button.configure(pady=8)
        button.pack(side="right", padx=(6, 0))
    week_board = tk.Frame(under_frame_3, bg=BORDER, height=210)
    week_board.pack(fill="x")
    week_board.pack_propagate(False)
    week_board.grid_propagate(False)
    week_board.rowconfigure(0, weight=1)
    for column in range(7):
        week_board.columnconfigure(column, weight=1, uniform="week")
    legend = tk.Frame(under_frame_3, bg=BG)
    legend.pack(fill="x", pady=(6, 8))
    for status, color in MAU_TRANG_THAI.items():
        make_label(legend, f"●  {status}", 9, color, bg=BG).pack(side="left", padx=(0, 18))

    detail = tk.Frame(under_frame_3, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    detail.pack(fill="both", expand=True)
    heading = tk.Frame(detail, bg=WHITE)
    heading.pack(fill="x", padx=16, pady=8)
    day_title, day_summary = tk.StringVar(window), tk.StringVar(window)
    make_label(heading, size=11, bold=True, textvariable=day_title).pack(side="left")
    make_label(heading, size=9, color=MUTED, textvariable=day_summary).pack(side="left", padx=12)
    add_button = make_button(heading, "+ Công việc", lambda: mo_form_cong_viec(planned_date=selected_day), True)
    add_button.configure(pady=6)
    add_button.pack(side="right")
    day_task_list = tao_bang(detail, (("name", "Công việc", 310), ("project", "Dự án", 190),
                                     ("due", "Hạn hoàn thành", 120), ("status", "Trạng thái", 120)), height=4)
    day_task_list.bind("<Double-1>", lambda event: sua_viec_da_chon(day_task_list))
    day_task_list.bind("<Return>", lambda event: sua_viec_da_chon(day_task_list))
    under_frame_3.bind("<Configure>", doi_kich_thuoc_lich)


def doi_kich_thuoc_lich(event):
    """Ưu tiên chừa chỗ cho bảng chi tiết khi thu thấp cửa sổ."""
    global week_card_limit
    height = min(220, max(140, event.height // 2 - 50))
    week_board.configure(height=height)
    limit = 1 if height < 185 else 2
    if limit != week_card_limit:
        week_card_limit = limit
        if week_tasks_by_day:
            ve_cac_ngay()


def cap_nhat_lich_tuan():
    """Xếp công việc theo ngày dự kiến, giữ việc không có ngày ở trang Kế hoạch."""
    global week_columns, week_tasks_by_day, selected_day
    try:
        tasks = cong_viec_trong_tuan(week_start)
    except sqlite3.Error as error:
        messagebox.showerror("Không thể tải lịch", database_error_message(error), parent=window)
        return False
    end = week_start + timedelta(days=6)
    week_title.set(f"{week_start:%d/%m/%Y} – {end:%d/%m/%Y}")
    week_tasks_by_day = {week_start + timedelta(days=offset): [] for offset in range(7)}
    for task in tasks:
        day = date.fromisoformat(task["planned_date"])
        week_tasks_by_day[day].append(task)
    ve_cac_ngay()
    return True


def ve_cac_ngay():
    """Vẽ lại bảy cột từ dữ liệu đã đọc, không truy vấn lại khi co cửa sổ."""
    global week_columns, selected_day
    for widget in week_board.winfo_children():
        widget.destroy()
    week_columns = {}
    for column, (day, day_tasks) in enumerate(week_tasks_by_day.items()):
        frame = tk.Frame(week_board, bg=WHITE, highlightthickness=1, highlightbackground=BORDER)
        frame.grid(row=0, column=column, sticky="nsew", padx=(0, 1) if column < 6 else 0)
        frame.grid_propagate(False)
        week_columns[day] = frame
        header = tk.Frame(frame, bg=WHITE)
        header.pack(fill="x", padx=10, pady=(8, 4))
        make_label(header, TEN_THU[day.weekday()], 9, MUTED).pack(anchor="w")
        make_label(header, f"{day.day:02d}", 18, BLUE if day == date.today() else TEXT, True).pack(anchor="w")
        for widget in (frame, header, *header.winfo_children()):
            widget.bind("<Button-1>", lambda event, chosen=day: chon_ngay(chosen))
        # Các việc còn lại luôn có đủ trong bảng bên dưới khi chọn ngày.
        for task in day_tasks[:week_card_limit]:
            block = tk.Frame(frame, bg=NEN_TRANG_THAI[task["status"]], padx=7, pady=4)
            block.pack(fill="x", padx=6, pady=(0, 5))
            name = task["name"] if len(task["name"]) <= 45 else task["name"][:44] + "…"
            label = make_label(block, name, 9, MAU_TRANG_THAI[task["status"]], bg=block["bg"])
            label.configure(height=2, anchor="nw")
            label.pack(fill="x")
            block.bind("<Configure>", lambda event, text=label: text.configure(wraplength=max(40, event.width - 14)))
            for widget in (block, label):
                widget.bind("<Button-1>", lambda event, chosen=day, task_id=task["id"]: chon_viec_tren_lich(chosen, task_id))
                widget.bind("<Double-1>", lambda event, task_id=task["id"]: mo_form_cong_viec(task_id=task_id))
        if len(day_tasks) > week_card_limit:
            more = make_label(frame, f"+{len(day_tasks) - week_card_limit} việc khác", 9, MUTED)
            more.pack(anchor="w", padx=10)
            more.bind("<Button-1>", lambda event, chosen=day: chon_ngay(chosen))
    if selected_day not in week_columns:
        selected_day = week_start
    chon_ngay(selected_day)


def chon_ngay(day):
    global selected_day, week_start
    previous_day, previous_week = selected_day, week_start
    selected_day = day
    if day not in week_columns:
        week_start = day - timedelta(days=day.weekday())
        if not cap_nhat_lich_tuan():
            selected_day, week_start = previous_day, previous_week
        return
    for current, frame in week_columns.items():
        frame.configure(highlightbackground=BLUE if current == day else BORDER,
                        highlightthickness=2 if current == day else 1)
    day_title.set(f"{TEN_THU[day.weekday()]}, {day:%d/%m/%Y}")
    tasks = week_tasks_by_day.get(day, [])
    day_summary.set(f"{len(tasks)} công việc" if tasks else "Chưa có công việc")
    selection = day_task_list.selection()
    items = day_task_list.get_children()
    if items:
        day_task_list.delete(*items)
    for task in tasks:
        day_task_list.insert("", "end", iid=str(task["id"]), tags=(task["status"],), values=(
            task["name"], task["project_name"], display_date(task["due_date"]), task["status"]))
    if selection and day_task_list.exists(selection[0]):
        day_task_list.selection_set(selection[0])


def chon_viec_tren_lich(day, task_id):
    chon_ngay(day)
    day_task_list.selection_set(str(task_id))
    day_task_list.see(str(task_id))


def chuyen_tuan(offset):
    global week_start, selected_day
    previous_week, previous_day = week_start, selected_day
    week_start += timedelta(weeks=offset)
    selected_day += timedelta(weeks=offset)
    if not cap_nhat_lich_tuan():
        week_start, selected_day = previous_week, previous_day


def ve_tuan_hien_tai():
    global week_start, selected_day
    previous_week, previous_day = week_start, selected_day
    selected_day = date.today()
    week_start = selected_day - timedelta(days=selected_day.weekday())
    if not cap_nhat_lich_tuan():
        week_start, selected_day = previous_week, previous_day


def build_interface():
    """Tạo giao diện một lần; các thao tác sau chỉ cập nhật nội dung và trạng thái."""
    global window, taskbar, under_frame_1, under_frame_2, under_frame_3
    global project_frame, contentbar, firstSay, title1, title2
    global button1, button2, button3, button_add, button_delete, project_list, project_count
    global content_title, content_description, start_text, end_text, project_badge
    global project_heading, description_label, empty_label
    global content_canvas, content_inner, content_window, status_text, page_title, page_subtitle
    global task_list, project_progress, project_progress_text
    global task_dialog, add_dialog, selected_project_id

    task_dialog, add_dialog, selected_project_id = None, None, None
    window = tk.Tk()
    window.title("Lịch dài hạn")
    window.geometry("1140x780")
    window.minsize(860, 600)
    window.configure(bg=BG)
    window.option_add("*Font", ("Segoe UI", 10))
    style = ttk.Style(window)
    style.theme_use("clam")
    style.configure("Project.Treeview", background=WHITE, fieldbackground=WHITE,
                    foreground=TEXT, rowheight=46, borderwidth=0, font=("Segoe UI", 11),
                    lightcolor=WHITE, darkcolor=WHITE)
    style.layout("Project.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.map("Project.Treeview", background=[("selected", LIGHT_BLUE)], foreground=[("selected", BLUE)])
    style.configure("Task.Treeview", background=WHITE, fieldbackground=WHITE, foreground=TEXT,
                    rowheight=34, borderwidth=0, font=("Segoe UI", 10))
    style.configure("Task.Treeview.Heading", background=SOFT, foreground=MUTED, relief="flat",
                    font=("Segoe UI", 9), padding=(8, 9))
    style.map("Task.Treeview", background=[("selected", LIGHT_BLUE)], foreground=[("selected", TEXT)])
    style.configure("Form.TCombobox", padding=(8, 7), fieldbackground=SOFT, foreground=TEXT)
    for key, status in (("todo", "Chưa làm"), ("doing", "Đang làm"), ("done", "Hoàn thành")):
        style.configure(f"{key}.Horizontal.TProgressbar", background=MAU_TRANG_THAI[status],
                        troughcolor="#EDF0F4", bordercolor="#EDF0F4", borderwidth=0, lightcolor=MAU_TRANG_THAI[status],
                        darkcolor=MAU_TRANG_THAI[status], thickness=7)
    style.configure("Form.TEntry", padding=(10, 9), fieldbackground=SOFT, foreground=TEXT,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
    style.map("Form.TEntry", bordercolor=[("focus", BLUE)], lightcolor=[("focus", BLUE)])
    style.configure("TScrollbar", background=BORDER, troughcolor=WHITE, borderwidth=0,
                    arrowsize=12, lightcolor=WHITE, darkcolor=WHITE)
    # Thanh cuộn mảnh bỏ các nút mũi tên để giảm chi tiết thừa trên giao diện.
    for direction, sticky in (("Vertical", "ns"), ("Horizontal", "we")):
        name = f"Slim.{direction}.TScrollbar"
        style.layout(name, [(f"{direction}.Scrollbar.trough", {
            "sticky": sticky,
            "children": [(f"{direction}.Scrollbar.thumb", {"expand": True, "sticky": "nswe"})],
        })])
        style.configure(name, background="#D4DEEC", troughcolor=SOFT, borderwidth=0,
                        lightcolor="#D4DEEC", darkcolor="#D4DEEC", arrowsize=8, gripcount=0)
        style.map(name, background=[("active", "#B4C5DF"), ("pressed", "#9BB3D8")])

    taskbar = tk.Frame(window, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    taskbar.pack(fill="x")
    title1 = make_label(taskbar, "Lịch dài hạn", 15, TEXT, True)
    title1.pack(side="left", padx=(28, 38), pady=20)
    button1 = make_button(taskbar, "Kế hoạch", show_frame1)
    button2 = make_button(taskbar, "Thống kê", show_frame2)
    button3 = make_button(taskbar, "Lịch tuần", show_frame3)
    for button in (button1, button2, button3):
        button.pack(side="left", padx=4, pady=12)
        button.bind("<Enter>", lambda event, b=button: b.configure(bg=LIGHT_BLUE))
        button.bind("<Leave>", lambda event, b=button: b.configure(
            bg=LIGHT_BLUE if b is active_nav_button else WHITE))

    page_title = tk.StringVar(window)
    page_subtitle = tk.StringVar(window)
    introduction = tk.Frame(window, bg=BG)
    introduction.pack(fill="x", padx=28, pady=(18, 16))
    firstSay = make_label(introduction, size=21, bold=True, bg=BG, textvariable=page_title)
    firstSay.pack(anchor="w")
    make_label(introduction, color=MUTED, bg=BG, textvariable=page_subtitle).pack(anchor="w", pady=(5, 0))

    # Dòng trạng thái được pack trước vùng mở rộng để luôn có chỗ ở đáy cửa sổ.
    status_text = tk.StringVar(window, "Sẵn sàng")
    make_label(window, size=9, color=MUTED, bg=BG, textvariable=status_text).pack(
        side="bottom", fill="x", padx=30, pady=(0, 12))
    under_frame_1 = tk.Frame(window, bg=BG)
    under_frame_2 = tk.Frame(window, bg=BG)
    under_frame_3 = tk.Frame(window, bg=BG)
    project_frame = tk.Frame(under_frame_1, bg=WHITE, width=230,
                            highlightbackground=BORDER, highlightthickness=1)
    project_frame.pack(side="left", fill="y", padx=(0, 18))
    project_frame.pack_propagate(False)
    contentbar = tk.Frame(under_frame_1, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    contentbar.pack(side="left", fill="both", expand=True)

    sidebar_heading = tk.Frame(project_frame, bg=WHITE)
    sidebar_heading.pack(fill="x", padx=18, pady=(22, 8))
    title2 = make_label(sidebar_heading, "Dự án", 13, TEXT, True)
    title2.pack(side="left")
    project_count = tk.StringVar(window, "0")
    make_label(sidebar_heading, color=BLUE, bold=True, bg=LIGHT_BLUE,
               textvariable=project_count, padx=8, pady=2).pack(side="right")
    make_label(project_frame, "Danh sách dự án", 9, MUTED).pack(anchor="w", padx=18, pady=(0, 14))
    footer = tk.Frame(project_frame, bg=WHITE)
    footer.pack(side="bottom", fill="x", padx=16, pady=16)
    button_add = make_button(footer, "+ Thêm dự án", show_project, primary=True)
    button_add.pack(fill="x")
    button_delete = make_button(footer, "Xóa dự án", xoa_du_an_dang_chon)
    button_delete.configure(fg="#A6524C", activeforeground="#A6524C", pady=7)
    button_delete.bind("<Enter>", lambda event: button_delete.configure(bg="#FAEEEE"))
    button_delete.bind("<Leave>", lambda event: button_delete.configure(bg=WHITE))
    button_delete.pack(fill="x", pady=(6, 0))
    tk.Frame(project_frame, bg=BORDER, height=1).pack(side="bottom", fill="x", padx=16)
    list_frame = tk.Frame(project_frame, bg=WHITE)
    list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 12))
    project_list = ttk.Treeview(list_frame, show="tree", selectmode="browse", style="Project.Treeview")
    vertical = ttk.Scrollbar(list_frame, orient="vertical", command=project_list.yview,
                             style="Slim.Vertical.TScrollbar")
    horizontal = ttk.Scrollbar(list_frame, orient="horizontal", command=project_list.xview,
                               style="Slim.Horizontal.TScrollbar")
    project_list.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    list_frame.rowconfigure(0, weight=1)
    list_frame.columnconfigure(0, weight=1)
    project_list.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    project_list.bind("<<TreeviewSelect>>", select_project)

    # Canvas giữ bố cục ổn định kể cả khi tên/mô tả dài hoặc cửa sổ thấp.
    content_canvas = tk.Canvas(contentbar, bg=WHITE, highlightthickness=0, yscrollincrement=20)
    content_scroll = ttk.Scrollbar(contentbar, command=content_canvas.yview,
                                   style="Slim.Vertical.TScrollbar")
    content_canvas.configure(yscrollcommand=content_scroll.set)
    content_scroll.pack(side="right", fill="y")
    content_canvas.pack(side="left", fill="both", expand=True)
    content_inner = tk.Frame(content_canvas, bg=WHITE, padx=24, pady=20)
    content_window = content_canvas.create_window((0, 0), window=content_inner, anchor="nw")
    content_inner.bind("<Configure>", lambda event: content_canvas.configure(scrollregion=content_canvas.bbox("all")))
    content_canvas.bind("<Configure>", resize_content)
    window.bind("<MouseWheel>", scroll_content)

    content_title = tk.StringVar(window)
    content_description = tk.StringVar(window)
    start_text = tk.StringVar(window)
    end_text = tk.StringVar(window)
    project_badge = tk.StringVar(window)
    project_heading = make_label(content_inner, size=21, bold=True, textvariable=content_title)
    project_heading.pack(fill="x", pady=(0, 5))
    tk.Frame(content_inner, bg=BORDER, height=1).pack(fill="x", pady=10)
    date_cards = tk.Frame(content_inner, bg=WHITE)
    date_cards.pack(fill="x")
    date_cards.columnconfigure((0, 1), weight=1, uniform="date_cards")
    for column, caption, value in ((0, "Bắt đầu", start_text), (1, "Kết thúc", end_text)):
        card = tk.Frame(date_cards, bg=WHITE, pady=4)
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 6) if column == 0 else (6, 0))
        make_label(card, caption, 9, MUTED).pack(anchor="w")
        make_label(card, size=11, textvariable=value).pack(anchor="w", pady=(4, 0))
    description_label = make_label(content_inner, size=10, color=MUTED, textvariable=content_description)
    description_label.pack(fill="x", pady=(10, 12))
    project_progress_text = tk.StringVar(window)
    make_label(content_inner, size=9, color=MUTED, textvariable=project_progress_text).pack(anchor="w", pady=(0, 7))
    project_progress = ttk.Progressbar(content_inner, maximum=100, style="doing.Horizontal.TProgressbar")
    project_progress.pack(fill="x")
    tk.Frame(content_inner, bg=BORDER, height=1).pack(fill="x", pady=12)
    heading = tk.Frame(content_inner, bg=WHITE)
    heading.pack(fill="x", pady=(0, 8))
    make_label(heading, "Công việc", 12, bold=True).pack(side="left")
    add_task_button = make_button(heading, "+ Công việc", lambda: mo_form_cong_viec(project_id=selected_project_id), True)
    add_task_button.configure(pady=7)
    add_task_button.pack(side="right")
    empty_label = make_label(content_inner, color=MUTED, size=9)
    empty_label.pack(fill="x", pady=(0, 6))
    task_list = tao_bang(content_inner, (("name", "Công việc", 260), ("planned", "Dự kiến", 100),
                                        ("due", "Hạn", 100), ("status", "Trạng thái", 110)), height=5, expand=False)
    task_list.bind("<Double-1>", lambda event: sua_viec_da_chon(task_list))
    task_list.bind("<Return>", lambda event: sua_viec_da_chon(task_list))
    actions = tk.Frame(content_inner, bg=WHITE)
    actions.pack(fill="x", pady=(8, 0))
    make_button(actions, "Sửa", lambda: sua_viec_da_chon(task_list)).pack(side="left")
    make_button(actions, "Xóa", lambda: xoa_viec_da_chon(task_list)).pack(side="left", padx=4)
    make_button(actions, "Đánh dấu xong", lambda: danh_dau_hoan_thanh(task_list)).pack(side="right")

    tao_trang_thong_ke()
    tao_trang_lich()
    show_empty_project()
    show_frame1()
    return window


def main():
    build_interface()
    # Cửa sổ đã có chủ sở hữu để mọi lỗi SQLite đều có thể báo bằng tiếng Việt.
    try:
        init_database()
    except sqlite3.Error as error:
        messagebox.showerror("Không thể khởi tạo dữ liệu", database_error_message(error), parent=window)
        window.destroy()
        return
    lam_moi_du_lieu()
    window.mainloop()


if __name__ == "__main__":
    main()
