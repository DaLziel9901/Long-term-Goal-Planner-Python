
"""Ứng dụng lịch dài hạn: giao diện Tkinter và dự án lưu bằng SQLite.

Chạy trực tiếp file này. Việc import chỉ nạp hàm, không mở cửa sổ hay tạo DB.
"""

import re
import sqlite3
import tkinter as tk
import tkinter.font as tkfont
import unicodedata
from contextlib import closing
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk


# Đường dẫn luôn cạnh source, kể cả khi chạy từ một thư mục Terminal khác.
DB_PATH = Path(__file__).resolve().with_name("calendar.db")
Sample = []  # Giữ tên biến cũ; được đồng bộ từ SQLite, không tự sinh dự án mẫu.

BG = "#F1F5FA"
WHITE = "#FFFFFF"
TEXT = "#1C2E4A"
MUTED = "#687991"
BLUE = "#2864E8"
BLUE_HOVER = "#1C50C7"
LIGHT_BLUE = "#EAF1FF"
BORDER = "#E0E7F0"
SOFT = "#F7F9FC"

window = None
add_dialog = None
active_nav_button = None
selected_project_id = None


# ---------------------------------------------------------------------------
# Tầng dữ liệu: không gọi widget Tkinter, có thể kiểm thử riêng hoặc dùng lại.
# ---------------------------------------------------------------------------
def connect_database():
    connection = sqlite3.connect(DB_PATH, timeout=3)
    connection.row_factory = sqlite3.Row
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
    content_title.set("Bắt đầu kế hoạch đầu tiên")
    content_description.set("Nhấn “+ Thêm dự án” ở bên trái để lưu tên, mô tả và thời gian thực hiện. "
                            "Dự án của bạn sẽ xuất hiện tại đây.")
    start_text.set("Chưa đặt ngày")
    end_text.set("Chưa đặt ngày")
    project_badge.set("CHƯA CÓ DỰ ÁN")
    content_canvas.yview_moveto(0)


def show_sample(exam):
    """Đọc dự án từ SQLite rồi cập nhật widget có sẵn, không tạo thêm cửa sổ."""
    global selected_project_id
    try:
        project = get_project(exam)
    except sqlite3.Error as error:
        messagebox.showerror("Không thể đọc dự án", database_error_message(error), parent=window)
        return
    if project is None:
        show_empty_project()
        return
    selected_project_id = project["id"]
    content_title.set(project["name"])
    content_description.set(project["description"] or "Dự án này chưa có mô tả.")
    start_text.set(display_date(project["start_date"]))
    end_text.set(display_date(project["end_date"]))
    project_badge.set(f"DỰ ÁN #{project['id']:02d}")
    item_id = str(project["id"])
    if project_list.exists(item_id):
        # Không gọi selection_set lặp lại để tránh vòng lặp TreeviewSelect.
        if project_list.selection() != (item_id,):
            project_list.selection_set(item_id)
        project_list.focus(item_id)
        project_list.see(item_id)
    content_canvas.yview_moveto(0)


def select_project(event=None):
    selected = project_list.selection()
    if selected:
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
    project_list.column("#0", width=column_width, minwidth=210, stretch=True)
    project_count.set(str(len(projects)))
    if projects:
        ids = {project["id"] for project in projects}
        show_sample(target if target in ids else projects[0]["id"])
    else:
        show_empty_project()
    return True


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
    make_label(header, "MỘT KHỞI ĐẦU MỚI", 9, BLUE, True, LIGHT_BLUE).pack(anchor="w")
    make_label(header, "Thêm dự án mới", 20, TEXT, True, LIGHT_BLUE).pack(anchor="w", pady=(5, 0))

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
    description_scroll = ttk.Scrollbar(description_box, command=description_text.yview)
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
            status_text.set("Đã lưu dự án. Bạn có thể đóng ứng dụng và tiếp tục vào lần sau.")
        else:
            status_text.set("Dự án đã lưu vào SQLite, nhưng chưa tải lại được danh sách.")
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
    # Chỉ cuộn vùng chi tiết, không chiếm thao tác cuộn Treeview hay ô nhập mô tả.
    widget = event.widget
    while widget is not None:
        if widget is content_canvas:
            if content_inner.winfo_reqheight() > content_canvas.winfo_height():
                direction = -1 if event.delta > 0 else 1
                content_canvas.yview_scroll(direction * max(1, abs(event.delta) // 120), "units")
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
        button1: ("Kế hoạch của bạn", "Từng dự án rõ ràng. Mỗi ngày thêm chủ động."),
        button2: ("Nhìn lại tiến độ", "Một góc nhìn tổng quan cho những kế hoạch dài hạn."),
        button3: ("Sắp xếp tuần mới", "Dành thời gian cho những điều quan trọng."),
    }
    page_title.set(headings[active_button][0])
    page_subtitle.set(headings[active_button][1])


def show_frame1():
    set_active_frame(under_frame_1, button1)


def show_frame2():
    set_active_frame(under_frame_2, button2)


def show_frame3():
    set_active_frame(under_frame_3, button3)


def create_placeholder(parent, title, description):
    """Trang chờ cùng phong cách, không đưa vào số liệu thống kê giả."""
    card = tk.Frame(parent, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    card.pack(fill="both", expand=True)
    make_label(card, "TRONG GIAI ĐOẠN TIẾP THEO", 9, BLUE, True).pack(anchor="w", padx=28, pady=(28, 12))
    make_label(card, title, 23, TEXT, True).pack(anchor="w", padx=28)
    label = make_label(card, description, 11, MUTED)
    label.pack(fill="x", padx=28, pady=14)
    make_button(card, "Về trang Kế hoạch", show_frame1, primary=True).pack(anchor="w", padx=28, pady=10)
    card.bind("<Configure>", lambda event: label.configure(wraplength=max(120, event.width - 56)))


def build_interface():
    """Tạo giao diện một lần; các thao tác sau chỉ cập nhật nội dung và trạng thái."""
    global window, taskbar, under_frame_1, under_frame_2, under_frame_3
    global project_frame, contentbar, firstSay, title1, title2
    global button1, button2, button3, button_add, project_list, project_count
    global content_title, content_description, start_text, end_text, project_badge
    global project_heading, description_label, empty_label
    global content_canvas, content_inner, content_window, status_text, page_title, page_subtitle

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
    style.configure("Form.TEntry", padding=(10, 9), fieldbackground=SOFT, foreground=TEXT,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
    style.map("Form.TEntry", bordercolor=[("focus", BLUE)], lightcolor=[("focus", BLUE)])
    style.configure("TScrollbar", background=BORDER, troughcolor=WHITE, borderwidth=0,
                    arrowsize=12, lightcolor=WHITE, darkcolor=WHITE)

    taskbar = tk.Frame(window, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    taskbar.pack(fill="x")
    make_label(taskbar, "L", 18, WHITE, True, BLUE, padx=12, pady=3).pack(side="left", padx=(28, 10), pady=16)
    title1 = make_label(taskbar, "Lịch dài hạn", 16, TEXT, True)
    title1.pack(side="left", padx=(0, 32))
    button1 = make_button(taskbar, "Kế hoạch", show_frame1)
    button2 = make_button(taskbar, "Thống kê", show_frame2)
    button3 = make_button(taskbar, "Lịch tuần", show_frame3)
    for button in (button1, button2, button3):
        button.pack(side="left", padx=4, pady=16)
        button.bind("<Enter>", lambda event, b=button: b.configure(bg=LIGHT_BLUE))
        button.bind("<Leave>", lambda event, b=button: b.configure(
            bg=LIGHT_BLUE if b is active_nav_button else WHITE))

    page_title = tk.StringVar(window)
    page_subtitle = tk.StringVar(window)
    introduction = tk.Frame(window, bg=BG)
    introduction.pack(fill="x", padx=28, pady=(24, 20))
    firstSay = make_label(introduction, size=25, bold=True, bg=BG, textvariable=page_title)
    firstSay.pack(anchor="w")
    make_label(introduction, color=MUTED, bg=BG, textvariable=page_subtitle).pack(anchor="w", pady=(5, 0))

    # Dòng trạng thái được pack trước vùng mở rộng để luôn có chỗ ở đáy cửa sổ.
    status_text = tk.StringVar(window, "Dữ liệu được lưu trên máy của bạn.")
    make_label(window, size=9, color=MUTED, bg=BG, textvariable=status_text).pack(
        side="bottom", fill="x", padx=30, pady=(0, 12))
    under_frame_1 = tk.Frame(window, bg=BG)
    under_frame_2 = tk.Frame(window, bg=BG)
    under_frame_3 = tk.Frame(window, bg=BG)
    project_frame = tk.Frame(under_frame_1, bg=WHITE, width=270,
                            highlightbackground=BORDER, highlightthickness=1)
    project_frame.pack(side="left", fill="y", padx=(0, 18))
    project_frame.pack_propagate(False)
    contentbar = tk.Frame(under_frame_1, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    contentbar.pack(side="left", fill="both", expand=True)

    sidebar_heading = tk.Frame(project_frame, bg=WHITE)
    sidebar_heading.pack(fill="x", padx=18, pady=(22, 8))
    title2 = make_label(sidebar_heading, "Dự án của tôi", 14, TEXT, True)
    title2.pack(side="left")
    project_count = tk.StringVar(window, "0")
    make_label(sidebar_heading, color=BLUE, bold=True, bg=LIGHT_BLUE,
               textvariable=project_count, padx=8, pady=2).pack(side="right")
    make_label(project_frame, "Chọn một dự án để bắt đầu", 9, MUTED).pack(anchor="w", padx=18, pady=(0, 18))
    footer = tk.Frame(project_frame, bg=WHITE)
    footer.pack(side="bottom", fill="x", padx=16, pady=16)
    button_add = make_button(footer, "+ Thêm dự án", show_project, primary=True)
    button_add.pack(fill="x")
    tk.Frame(project_frame, bg=BORDER, height=1).pack(side="bottom", fill="x", padx=16)
    list_frame = tk.Frame(project_frame, bg=WHITE)
    list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 12))
    project_list = ttk.Treeview(list_frame, show="tree", selectmode="browse", style="Project.Treeview")
    vertical = ttk.Scrollbar(list_frame, orient="vertical", command=project_list.yview)
    horizontal = ttk.Scrollbar(list_frame, orient="horizontal", command=project_list.xview)
    project_list.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    list_frame.rowconfigure(0, weight=1)
    list_frame.columnconfigure(0, weight=1)
    project_list.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    project_list.bind("<<TreeviewSelect>>", select_project)

    # Canvas giữ bố cục ổn định kể cả khi tên/mô tả dài hoặc cửa sổ thấp.
    content_canvas = tk.Canvas(contentbar, bg=WHITE, highlightthickness=0, yscrollincrement=20)
    content_scroll = ttk.Scrollbar(contentbar, command=content_canvas.yview)
    content_canvas.configure(yscrollcommand=content_scroll.set)
    content_scroll.pack(side="right", fill="y")
    content_canvas.pack(side="left", fill="both", expand=True)
    content_inner = tk.Frame(content_canvas, bg=WHITE, padx=28, pady=26)
    content_window = content_canvas.create_window((0, 0), window=content_inner, anchor="nw")
    content_inner.bind("<Configure>", lambda event: content_canvas.configure(scrollregion=content_canvas.bbox("all")))
    content_canvas.bind("<Configure>", resize_content)
    window.bind("<MouseWheel>", scroll_content)

    content_title = tk.StringVar(window)
    content_description = tk.StringVar(window)
    start_text = tk.StringVar(window)
    end_text = tk.StringVar(window)
    project_badge = tk.StringVar(window)
    make_label(content_inner, "CHI TIẾT DỰ ÁN", 9, BLUE, True).pack(anchor="w")
    project_heading = make_label(content_inner, size=25, bold=True, textvariable=content_title)
    project_heading.pack(fill="x", pady=(12, 10))
    make_label(content_inner, size=9, color=MUTED, textvariable=project_badge).pack(anchor="w")
    tk.Frame(content_inner, bg=BORDER, height=1).pack(fill="x", pady=22)
    make_label(content_inner, "Thời gian thực hiện", 11, TEXT, True).pack(anchor="w", pady=(0, 12))
    date_cards = tk.Frame(content_inner, bg=WHITE)
    date_cards.pack(fill="x")
    date_cards.columnconfigure((0, 1), weight=1, uniform="date_cards")
    for column, caption, value in ((0, "NGÀY BẮT ĐẦU", start_text), (1, "NGÀY KẾT THÚC", end_text)):
        card = tk.Frame(date_cards, bg=SOFT, padx=14, pady=14,
                        highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 6) if column == 0 else (6, 0))
        make_label(card, caption, 9, MUTED, bg=SOFT).pack(anchor="w")
        make_label(card, size=12, bold=True, bg=SOFT, textvariable=value).pack(anchor="w", pady=(7, 0))
    make_label(content_inner, "Về dự án", 12, TEXT, True).pack(anchor="w", pady=(24, 10))
    description_label = make_label(content_inner, size=11, color=MUTED, textvariable=content_description)
    description_label.pack(fill="x")
    tk.Frame(content_inner, bg=BORDER, height=1).pack(fill="x", pady=24)
    make_label(content_inner, "Công việc", 12, TEXT, True).pack(anchor="w")
    empty_label = make_label(content_inner,
        "Khu vực công việc sẽ được bổ sung trong giai đoạn tiếp theo.\n"
        "Hiện bạn có thể tạo dự án và lưu thông tin để tiếp tục xây dựng kế hoạch.", 10, MUTED)
    empty_label.pack(fill="x", pady=(10, 0))

    create_placeholder(under_frame_2, "Theo dõi tiến độ, từ dữ liệu thật",
                       "Khi có chức năng quản lý công việc, trang này sẽ tổng hợp tiến độ của từng dự án. "
                       "Hiện chưa có dữ liệu công việc để tính thống kê.")
    create_placeholder(under_frame_3, "Một tuần được sắp xếp rõ ràng",
                       "Lịch tuần sẽ dùng chung dữ liệu công việc với trang Kế hoạch. "
                       "Bạn có thể chuẩn bị các dự án trước khi chức năng này được bổ sung.")
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
    refresh_project_list()
    window.mainloop()


if __name__ == "__main__":
    main()
