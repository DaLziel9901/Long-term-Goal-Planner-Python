"""Xử lý nút bấm, chuyển trang và tải lại dữ liệu."""


import sqlite3
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, ttk

from database import calc_progress, get_task_by_id
from ui import data, state
from ui.widgets import (BLUE, LIGHT_BLUE, MUTED, WHITE)


def show_empty_project():
    state.selected_project_id = None
    state.content_title.set('Chưa có mục tiêu')
    state.content_description.set('Thêm một mục tiêu ở bên trái hoặc trong Lịch mục tiêu để bắt đầu.')
    state.start_text.set('Chưa đặt ngày')
    state.end_text.set('Chưa đặt ngày')
    state.project_badge.set('')
    cap_nhat_cong_viec([])
    state.content_canvas.yview_moveto(0)


def show_sample(exam):
    """Đọc dự án từ SQLite rồi cập nhật widget có sẵn, không tạo thêm cửa sổ."""
    try:
        project = data.get_project(exam)
        tasks = data.danh_sach_cong_viec(project['id']) if project else []
    except sqlite3.Error as error:
        previous = str(state.selected_project_id)
        if state.selected_project_id is not None and state.project_list.exists(previous):
            if state.project_list.selection() != (previous,):
                state.project_list.selection_set(previous)
        elif state.project_list.selection():
            state.project_list.selection_remove(*state.project_list.selection())
        messagebox.showerror('Không thể đọc dự án', data.database_error_message(error), parent=state.window)
        return False
    if project is None:
        show_empty_project()
        return True
    state.selected_project_id = project['id']
    state.content_title.set(project['name'])
    state.content_description.set(project['description'] or 'Mục này chưa có mô tả.')
    state.start_text.set(data.display_date(project['start_date']))
    state.end_text.set(data.display_date(project['end_date']))
    cap_nhat_cong_viec(tasks)
    item_id = str(project['id'])
    if state.project_list.exists(item_id):
        if state.project_list.selection() != (item_id,):
            state.project_list.selection_set(item_id)
        state.project_list.focus(item_id)
        state.project_list.see(item_id)
    elif state.project_list.selection():
        state.project_list.selection_remove(*state.project_list.selection())
    state.content_canvas.yview_moveto(0)
    return True


def select_project(event=None):
    selected = state.project_list.selection()
    if selected and int(selected[0]) != state.selected_project_id:
        show_sample(int(selected[0]))


def refresh_project_list(select_id=None):
    """Đọc DB trước khi thay danh sách; dùng ID ổn định làm iid của Treeview."""
    try:
        projects = data.load_projects()
    except sqlite3.Error as error:
        messagebox.showerror('Không thể tải dự án', data.database_error_message(error), parent=state.window)
        return False
    target = select_id if select_id is not None else state.selected_project_id
    state.Sample[:] = [project['name'] for project in projects]
    items = state.project_list.get_children()
    if items:
        state.project_list.delete(*items)
    for project in projects:
        state.project_list.insert('', 'end', iid=str(project['id']), text=project['name'])
    font = tkfont.Font(family='Segoe UI', size=11)
    column_width = max([210] + [font.measure(name) + 30 for name in state.Sample])
    state.project_list.column('#0', width=column_width, minwidth=210, stretch=False)
    state.project_count.set(str(len(projects)))
    if projects:
        try:
            task = get_task_by_id(target) if target is not None else None
        except sqlite3.Error as error:
            messagebox.showerror('Không thể tải công việc',
                data.database_error_message(error),
                parent=state.window)
            return False
        return show_sample(task['id'] if task else projects[0]['id'])
    else:
        show_empty_project()
    return True


def xoa_du_an_dang_chon():
    """Hỏi xác nhận trước khi xóa; chỉ đổi giao diện sau khi commit thành công."""
    project_id = state.selected_project_id
    if project_id is None:
        messagebox.showinfo('Chọn dự án',
            'Bạn hãy chọn dự án cần xóa ở danh sách bên trái.',
            parent=state.window)
        return
    try:
        project = data.get_project(project_id)
        if project is None:
            raise ValueError('Dự án không còn tồn tại. Vui lòng tải lại danh sách.')
        count = len(data.danh_sach_cong_viec(project_id))
    except (sqlite3.Error, ValueError) as error:
        text = data.database_error_message(error) if isinstance(error, sqlite3.Error) else str(error)
        messagebox.showerror('Không thể đọc dự án', text, parent=state.window)
        return
    name = project['name']
    if len(name) > 160:
        name = name[:159] + '…'
    detail = 'Toàn bộ công việc con ở mọi cấp cũng sẽ bị xóa.' if count else 'Mục này chưa có công việc con.'
    confirmed = messagebox.askyesno('Xóa dự án',
        f'Xóa dự án “{name}”?\n\n{detail}\nThao tác này không thể hoàn tác.',
        parent=state.window,
        default=messagebox.NO)
    if not confirmed:
        return
    try:
        data.xoa_du_an(project_id)
    except (sqlite3.Error, ValueError) as error:
        text = data.database_error_message(error) if isinstance(error, sqlite3.Error) else str(error)
        messagebox.showerror('Chưa xóa được dự án', text, parent=state.window)
        return
    if lam_moi_du_lieu(project['parent_id']):
        state.status_text.set('Đã xóa dự án và các công việc thuộc dự án.')
    else:
        state.status_text.set('Đã xóa dự án, chưa tải lại được đầy đủ dữ liệu.')


def show_project():
    """Giữ hàm nhập dự án của bản cũ; chuyển việc nhập sang hộp thoại đầy đủ."""
    from ui import forms
    return forms.open_add_project()


def resize_content(event):
    """Giữ nội dung vừa chiều ngang; chiều dọc có thanh cuộn khi văn bản dài."""
    state.content_canvas.itemconfigure(state.content_window, width=event.width)
    width = max(120, event.width - 56)
    for label in (state.project_heading, state.description_label, state.empty_label):
        label.configure(wraplength=width)


def scroll_content(event):
    if isinstance(event.widget, (ttk.Treeview, tk.Text, ttk.Combobox)):
        return None
    widget = event.widget
    while widget is not None:
        if widget in (state.content_canvas, state.stats_canvas):
            bounds = widget.bbox('all')
            if bounds and bounds[3] > widget.winfo_height():
                direction = -1 if event.delta > 0 else 1
                widget.yview_scroll(direction * max(1, abs(event.delta) // 120), 'units')
                return 'break'
            return None
        widget = getattr(widget, 'master', None)


def set_active_frame(frame, active_button):
    for page in (state.under_frame_1, state.under_frame_2, state.under_frame_3):
        page.pack_forget()
    frame.pack(fill='both', expand=True, padx=28, pady=(0, 12))
    # Tab lịch dành toàn bộ chiều cao cho lịch và danh sách công việc.
    introduction = state.firstSay.master
    if active_button is state.button3:
        introduction.pack_forget()
    else:
        introduction.pack(fill='x', padx=28, pady=(18, 16), before=frame)
    state.active_nav_button = active_button
    for button in (state.button1, state.button2, state.button3):
        selected = button is active_button
        button.configure(bg=LIGHT_BLUE if selected else WHITE, fg=BLUE if selected else MUTED)
    headings = {state.button1: ('Kế hoạch', 'Mục tiêu và công việc của bạn'),
        state.button2: ('Thống kê', 'Tiến độ và trạng thái công việc'),
        state.button3: ('Lịch mục tiêu', 'Thời gian, tiến độ và những việc cần làm')}
    state.page_title.set(headings[active_button][0])
    state.page_subtitle.set(headings[active_button][1])


def show_frame1():
    set_active_frame(state.under_frame_1, state.button1)


def show_frame2():
    from ui import statistics
    statistics.cap_nhat_thong_ke()
    set_active_frame(state.under_frame_2, state.button2)


def show_frame3():
    from ui import weekly_calendar
    weekly_calendar.cap_nhat_lich_tuan()
    set_active_frame(state.under_frame_3, state.button3)


def cap_nhat_cong_viec(tasks=None):
    """Nạp công việc của dự án đang chọn và tính tiến độ thực tế."""
    if tasks is None:
        try:
            tasks = data.danh_sach_cong_viec(state.selected_project_id) if state.selected_project_id else []
        except sqlite3.Error as error:
            messagebox.showerror('Không thể đọc công việc',
                data.database_error_message(error),
                parent=state.window)
            return False
    try:
        progress = calc_progress(state.selected_project_id) if state.selected_project_id is not None else 0
    except sqlite3.Error as error:
        messagebox.showerror('Không thể tính tiến độ',
            data.database_error_message(error),
            parent=state.window)
        return False
    selection = state.task_list.selection()
    items = state.task_list.get_children()
    if items:
        state.task_list.delete(*items)
    for task in tasks:
        state.task_list.insert('',
            'end',
            iid=str(task['id']),
            tags=(task['status'],),
            values=(task['name'], data.display_date(task['planned_date']), data.display_date(task['due_date']), task['status']))
    if selection and state.task_list.exists(selection[0]):
        state.task_list.selection_set(selection[0])
    done = sum((task['status'] == 'Hoàn thành' for task in tasks))
    state.project_progress.configure(value=progress)
    state.project_progress_text.set(f'{done}/{len(tasks)} công việc con hoàn thành · Tiến độ: {progress:g}%')
    state.project_badge.set(f'{len(tasks)} công việc')
    if tasks:
        state.empty_label.pack_forget()
    else:
        state.empty_label.configure(text='Chưa có công việc. Nhấn “+ Công việc” để thêm.')
        state.empty_label.pack(fill='x', pady=(0, 6), before=state.task_list.master)
    return True


def lam_moi_du_lieu(project_id=None):
    """Sau mỗi lần lưu, ba trang cùng đọc lại một nguồn dữ liệu SQLite."""
    from ui import statistics, weekly_calendar
    result = refresh_project_list(select_id=project_id)
    result = statistics.cap_nhat_thong_ke() and result
    result = weekly_calendar.cap_nhat_lich_tuan() and result
    return result


def chon_cong_viec(tree):
    selected = tree.selection()
    if not selected or not selected[0].isdigit():
        messagebox.showinfo('Chọn công việc',
            'Bạn hãy chọn một công việc trong danh sách.',
            parent=state.window)
        return None
    return int(selected[0])


def sua_viec_da_chon(tree):
    from ui import forms
    task_id = chon_cong_viec(tree)
    if task_id is not None:
        forms.mo_form_cong_viec(task_id=task_id)


def mo_viec_da_chon():
    task_id = chon_cong_viec(state.task_list)
    if task_id is not None:
        show_sample(task_id)


def ve_task_cha():
    try:
        task = get_task_by_id(state.selected_project_id)
        if task and task['parent_id'] is not None:
            show_sample(task['parent_id'])
    except sqlite3.Error as error:
        messagebox.showerror('Không thể đọc task cha',
            data.database_error_message(error),
            parent=state.window)


def sua_task_hien_tai():
    from ui import forms
    if state.selected_project_id is not None:
        forms.mo_form_cong_viec(task_id=state.selected_project_id)


def doi_trang_thai_hien_tai():
    if state.selected_project_id is None:
        return
    try:
        task = get_task_by_id(state.selected_project_id)
        if task is None:
            raise ValueError('Task không còn tồn tại.')
        data.doi_trang_thai(task['id'], 'Chưa làm' if task['is_done'] else 'Hoàn thành')
    except (sqlite3.Error, ValueError) as error:
        text = data.database_error_message(error) if isinstance(error, sqlite3.Error) else str(error)
        messagebox.showerror('Chưa cập nhật được', text, parent=state.window)
        return
    lam_moi_du_lieu(task['id'])


def xoa_viec_da_chon(tree):
    task_id = chon_cong_viec(tree)
    if task_id is None or not messagebox.askyesno('Xóa công việc',
        'Xóa công việc đã chọn và toàn bộ con cháu?',
        parent=state.window):
        return
    try:
        data.xoa_cong_viec(task_id)
    except (sqlite3.Error, ValueError) as error:
        text = data.database_error_message(error) if isinstance(error, sqlite3.Error) else str(error)
        messagebox.showerror('Chưa xóa được công việc', text, parent=state.window)
        return
    lam_moi_du_lieu()
    state.status_text.set('Đã xóa công việc.')


def danh_dau_hoan_thanh(tree):
    task_id = chon_cong_viec(tree)
    if task_id is None:
        return
    try:
        data.doi_trang_thai(task_id, 'Hoàn thành')
    except (sqlite3.Error, ValueError) as error:
        text = data.database_error_message(error) if isinstance(error, sqlite3.Error) else str(error)
        messagebox.showerror('Chưa cập nhật được', text, parent=state.window)
        return
    lam_moi_du_lieu()
    state.status_text.set('Đã đánh dấu hoàn thành.')
