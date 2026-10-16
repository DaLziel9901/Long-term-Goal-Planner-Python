"""Biểu mẫu thêm dự án và thêm/sửa công việc."""


import sqlite3
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

from database import get_children
from ui import actions, data, state, widgets
from ui.widgets import (BLUE, BORDER, LIGHT_BLUE, MUTED, SOFT, TEXT, WHITE)


def open_add_project():
    """Chỉ mở một Toplevel; Lưu kiểm tra dữ liệu rồi commit trước khi refresh."""
    if state.add_dialog is not None and state.add_dialog.winfo_exists():
        state.add_dialog.lift()
        state.add_dialog.focus_set()
        return state.add_dialog
    dialog = tk.Toplevel(state.window)
    state.add_dialog = dialog
    dialog.withdraw()
    dialog.title('Thêm dự án mới')
    dialog.configure(bg=WHITE)
    dialog.resizable(False, False)
    dialog.transient(state.window)

    def close_dialog(event=None):
        dialog.grab_release()
        dialog.destroy()
        state.add_dialog = None
        state.button_add.focus_set()
    dialog.protocol('WM_DELETE_WINDOW', close_dialog)
    dialog.bind('<Escape>', close_dialog)
    header = tk.Frame(dialog, bg=LIGHT_BLUE, padx=28, pady=20)
    header.pack(fill='x')
    widgets.make_label(header, 'Thêm dự án', 19, TEXT, True, LIGHT_BLUE).pack(anchor='w')
    form = tk.Frame(dialog, bg=WHITE, padx=28, pady=20)
    form.pack(fill='both', expand=True)
    widgets.make_label(form, 'Tên dự án *', bold=True).pack(anchor='w', pady=(0, 7))
    name_entry = ttk.Entry(form, style='Form.TEntry')
    name_entry.pack(fill='x')
    widgets.make_label(form, 'Mô tả', bold=True).pack(anchor='w', pady=(18, 7))
    description_box = tk.Frame(form, bg=BORDER, padx=1, pady=1)
    description_box.pack(fill='x')
    description_text = tk.Text(description_box,
        height=4,
        width=48,
        wrap='word',
        relief='flat',
        bg=SOFT,
        fg=TEXT,
        font=('Segoe UI', 10),
        padx=10,
        pady=9,
        insertbackground=BLUE,
        undo=True)
    description_scroll = ttk.Scrollbar(description_box,
        command=description_text.yview,
        style='Slim.Vertical.TScrollbar')
    description_text.configure(yscrollcommand=description_scroll.set)
    description_scroll.pack(side='right', fill='y')
    description_text.pack(side='left', fill='both', expand=True)
    dates = tk.Frame(form, bg=WHITE)
    dates.pack(fill='x', pady=(18, 0))
    dates.columnconfigure((0, 1), weight=1, uniform='dates')
    widgets.make_label(dates, 'Ngày bắt đầu', bold=True).grid(row=0, column=0, sticky='w', pady=(0, 7))
    widgets.make_label(dates,
        'Ngày kết thúc',
        bold=True).grid(row=0,
        column=1,
        sticky='w',
        padx=(12, 0),
        pady=(0, 7))
    start_entry = ttk.Entry(dates, width=20, style='Form.TEntry')
    end_entry = ttk.Entry(dates, width=20, style='Form.TEntry')
    start_entry.grid(row=1, column=0, sticky='ew', padx=(0, 6))
    end_entry.grid(row=1, column=1, sticky='ew', padx=(12, 0))
    widgets.make_label(form,
        'DD/MM/YYYY · Có thể để trống ngày và mô tả',
        9,
        MUTED).pack(anchor='w',
        pady=(8, 0))

    def save_project(event=None):
        try:
            project_id = data.add_project(name_entry.get(),
                description_text.get('1.0', 'end-1c'),
                start_entry.get(),
                end_entry.get())
        except ValueError as error:
            messagebox.showwarning('Kiểm tra thông tin', str(error), parent=dialog)
            return 'break'
        except sqlite3.Error as error:
            messagebox.showerror('Chưa lưu được dự án', data.database_error_message(error), parent=dialog)
            return 'break'
        close_dialog()
        if actions.refresh_project_list(select_id=project_id):
            state.status_text.set('Đã thêm dự án.')
        else:
            state.status_text.set('Đã lưu dự án, chưa tải lại được danh sách.')
        return 'break'
    footer = tk.Frame(dialog, bg=SOFT, padx=28, pady=16)
    footer.pack(fill='x')
    save_button = widgets.make_button(footer, 'Lưu dự án', save_project, primary=True)
    save_button.pack(side='right')
    widgets.make_button(footer, 'Hủy', close_dialog).pack(side='right', padx=(0, 10))
    name_entry.bind('<Return>', save_project)
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
    x = state.window.winfo_rootx() + (state.window.winfo_width() - width) // 2
    y = state.window.winfo_rooty() + (state.window.winfo_height() - height) // 2
    x = max(0, min(x, dialog.winfo_screenwidth() - width))
    y = max(0, min(y, dialog.winfo_screenheight() - height - 60))
    dialog.geometry(f'{width}x{height}+{x}+{y}')
    dialog.deiconify()
    dialog.wait_visibility()
    dialog.grab_set()
    name_entry.focus_set()
    return dialog


def mo_form_cong_viec(task_id=None, project_id=None, planned_date=None):
    """Một form dùng cho thêm và sửa công việc, không tạo thêm cửa sổ Tk."""
    if state.task_dialog is not None and state.task_dialog.winfo_exists():
        state.task_dialog.lift()
        state.task_dialog.focus_set()
        return state.task_dialog
    try:
        projects = data.load_projects()
        task = data.lay_cong_viec(task_id) if task_id is not None else None
        if task:
            projects = [data.get_project(task['parent_id'])] if task['parent_id'] is not None else [task]
        parent = data.get_project(project_id) if project_id is not None else None
        if parent is not None and all((project['id'] != parent['id'] for project in projects)):
            projects.append(parent)
        has_children = bool(get_children(task_id)) if task else False
    except sqlite3.Error as error:
        messagebox.showerror('Không thể đọc dữ liệu', data.database_error_message(error), parent=state.window)
        return None
    if not projects:
        messagebox.showinfo('Chưa có dự án',
            'Hãy thêm một dự án trước khi tạo công việc.',
            parent=state.window)
        return None
    if task_id is not None and task is None:
        messagebox.showinfo('Không tìm thấy', 'Công việc này không còn tồn tại.', parent=state.window)
        return None
    dialog = tk.Toplevel(state.window)
    state.task_dialog = dialog
    dialog.withdraw()
    dialog.title('Sửa công việc' if task else 'Thêm công việc')
    dialog.configure(bg=WHITE)
    dialog.transient(state.window)
    dialog.resizable(False, False)

    def dong_form(event=None):
        dialog.grab_release()
        dialog.destroy()
        state.task_dialog = None
        state.window.focus_set()
    dialog.protocol('WM_DELETE_WINDOW', dong_form)
    dialog.bind('<Escape>', dong_form)
    form = tk.Frame(dialog, bg=WHITE, padx=24, pady=22)
    form.pack(fill='both', expand=True)
    widgets.make_label(form,
        'Sửa công việc' if task else 'Thêm công việc',
        19,
        bold=True).pack(anchor='w',
        pady=(0, 18))
    widgets.make_label(form, 'Mục tiêu cha (giữ nguyên khi sửa)', bold=True).pack(anchor='w', pady=(0, 6))
    project_combo = ttk.Combobox(form,
        values=[project['name'] for project in projects],
        state='readonly',
        style='Form.TCombobox',
        width=48)
    default_project = task['project_id'] if task else project_id or state.selected_project_id
    index = next((i for i, project in enumerate(projects) if project['id'] == default_project), 0)
    project_combo.current(index)
    if task or project_id is not None:
        project_combo.configure(state='disabled')
    project_combo.pack(fill='x')
    widgets.make_label(form, 'Tên công việc *', bold=True).pack(anchor='w', pady=(14, 6))
    name_entry = ttk.Entry(form, style='Form.TEntry')
    name_entry.pack(fill='x')
    widgets.make_label(form, 'Ghi chú', bold=True).pack(anchor='w', pady=(14, 6))
    text_frame = tk.Frame(form, bg=BORDER, padx=1, pady=1)
    text_frame.pack(fill='x')
    description_text = tk.Text(text_frame,
        height=3,
        width=48,
        wrap='word',
        font=('Segoe UI', 10),
        bg=SOFT,
        fg=TEXT,
        relief='flat',
        padx=9,
        pady=8,
        undo=True)
    scrollbar = ttk.Scrollbar(text_frame, command=description_text.yview, style='Slim.Vertical.TScrollbar')
    description_text.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side='right', fill='y')
    description_text.pack(side='left', fill='both', expand=True)
    dates = tk.Frame(form, bg=WHITE)
    dates.pack(fill='x', pady=(14, 0))
    dates.columnconfigure((0, 1), weight=1, uniform='dates')
    widgets.make_label(dates, 'Ngày dự kiến').grid(row=0, column=0, sticky='w', pady=(0, 6))
    widgets.make_label(dates, 'Hạn hoàn thành').grid(row=0, column=1, sticky='w', padx=(12, 0), pady=(0, 6))
    start_entry = ttk.Entry(dates, width=20, style='Form.TEntry')
    end_entry = ttk.Entry(dates, width=20, style='Form.TEntry')
    start_entry.grid(row=1, column=0, sticky='ew', padx=(0, 6))
    end_entry.grid(row=1, column=1, sticky='ew', padx=(12, 0))
    widgets.make_label(form,
        'DD/MM/YYYY · Để trống nếu chưa xếp lịch',
        9,
        MUTED).pack(anchor='w',
        pady=(7, 14))
    widgets.make_label(form, 'Trạng thái', bold=True).pack(anchor='w', pady=(0, 6))
    status_combo = ttk.Combobox(form,
        values=data.TRANG_THAI_CONG_VIEC,
        state='readonly',
        style='Form.TCombobox')
    status_combo.set(task['status'] if task else 'Chưa làm')
    if has_children:
        status_combo.configure(state='disabled')
    status_combo.pack(fill='x')
    if has_children:
        widgets.make_label(form, 'Tiến độ được tính tự động từ các công việc con.', 9, MUTED).pack(anchor='w')
    if task:
        widgets.make_label(form,
            'Ngày đã lưu chỉ có thể sửa, chưa hỗ trợ xóa trống.',
            9,
            MUTED).pack(anchor='w')
    if task:
        name_entry.insert(0, task['name'])
        description_text.insert('1.0', task['description'] or '')
        start_entry.insert(0, data.display_date(task['planned_date']) if task['planned_date'] else '')
        end_entry.insert(0, data.display_date(task['due_date']) if task['due_date'] else '')
    elif planned_date:
        start_entry.insert(0, planned_date.strftime('%d/%m/%Y'))

    def luu_viec(event=None):
        chosen_project = projects[project_combo.current()]['id']
        values = (name_entry.get(),
            description_text.get('1.0', 'end-1c'),
            start_entry.get(),
            end_entry.get(),
            status_combo.get())
        try:
            if task:
                data.sua_cong_viec(task_id, *values)
                saved_id = task_id
            else:
                saved_id = data.them_cong_viec(chosen_project, *values)
        except ValueError as error:
            messagebox.showwarning('Kiểm tra thông tin', str(error), parent=dialog)
            return 'break'
        except sqlite3.Error as error:
            messagebox.showerror('Chưa lưu được công việc', data.database_error_message(error), parent=dialog)
            return 'break'
        if state.active_nav_button is state.button3 and start_entry.get().strip():
            state.selected_day = datetime.strptime(start_entry.get().strip(), '%d/%m/%Y').date()
            state.week_start = state.selected_day - timedelta(days=state.selected_day.weekday())
        # Chỉ tải lại các trang khi hàm database đã lưu thành công.
        dong_form()
        if actions.lam_moi_du_lieu(task_id if task else chosen_project):
            state.status_text.set('Đã lưu công việc.')
        else:
            state.status_text.set('Đã lưu công việc, chưa tải lại được đầy đủ dữ liệu.')
        for tree in (state.task_list, state.day_task_list):
            if tree.exists(str(saved_id)):
                tree.selection_set(str(saved_id))
                tree.see(str(saved_id))
        return 'break'
    footer = tk.Frame(dialog, bg=SOFT, padx=24, pady=14)
    footer.pack(fill='x')
    save_button = widgets.make_button(footer, 'Lưu công việc', luu_viec, primary=True)
    save_button.pack(side='right')
    widgets.make_button(footer, 'Hủy', dong_form).pack(side='right', padx=(0, 10))
    name_entry.bind('<Return>', luu_viec)
    dialog.name_entry = name_entry
    dialog.description_text = description_text
    dialog.start_entry = start_entry
    dialog.end_entry = end_entry
    dialog.status_combo = status_combo
    dialog.project_combo = project_combo
    dialog.save_button = save_button
    dialog.save_task = luu_viec
    dialog.close_dialog = dong_form
    dialog.update_idletasks()
    width, height = (max(540, dialog.winfo_reqwidth()), dialog.winfo_reqheight())
    x = max(0, state.window.winfo_rootx() + (state.window.winfo_width() - width) // 2)
    y = max(0, state.window.winfo_rooty() + (state.window.winfo_height() - height) // 2)
    x = max(0, min(x, dialog.winfo_screenwidth() - width))
    y = max(0, min(y, dialog.winfo_screenheight() - height - 60))
    dialog.geometry(f'{width}x{height}+{x}+{y}')
    dialog.deiconify()
    dialog.wait_visibility()
    dialog.grab_set()
    name_entry.focus_set()
    return dialog
