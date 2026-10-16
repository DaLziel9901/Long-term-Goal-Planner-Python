"""Lịch mục tiêu dài hạn; giữ tên hàm cũ để các callback tiếp tục hoạt động."""

import sqlite3
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from ui import actions, calendar_data, data, forms, state, timeline, widgets
from ui.widgets import BG, BLUE, BORDER, MUTED, WHITE


def calendar_button(parent, text, command, primary=False):
    button = widgets.make_button(parent, text, command, primary)
    button.configure(pady=5, padx=10)
    return button


def tao_trang_lich():
    state.selected_day = date.today()
    state.week_start = state.selected_day - timedelta(days=state.selected_day.weekday())
    state.calendar_tasks = []
    state.calendar_collapsed = set()
    state.calendar_selected_task = None
    state.calendar_mode = tk.StringVar(state.window, 'Tuần')
    state.calendar_include_done = tk.BooleanVar(state.window, False)
    state.week_title = tk.StringVar(state.window)
    state.calendar_selection_text = tk.StringVar(state.window, 'Chọn một mục tiêu trên lịch để thao tác.')
    state.under_frame_3.columnconfigure(0, weight=1)
    state.under_frame_3.rowconfigure(1, weight=1)

    toolbar = tk.Frame(state.under_frame_3, bg=BG)
    toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 6))
    calendar_button(toolbar, '+ Mục tiêu', forms.open_add_project, True).pack(side='left')
    calendar_button(toolbar, 'Hôm nay', ve_tuan_hien_tai).pack(side='right')
    calendar_button(toolbar, 'Tuần sau ›', lambda: chuyen_tuan(1)).pack(side='right', padx=4)
    calendar_button(toolbar, '‹ Tuần trước', lambda: chuyen_tuan(-1)).pack(side='right')
    widgets.make_label(toolbar, textvariable=state.week_title, bg=BG, size=10).pack(side='left', padx=12)

    board = tk.Frame(state.under_frame_3, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    board.grid(row=1, column=0, sticky='nsew')
    board.columnconfigure(1, weight=1)
    board.rowconfigure(1, weight=1)
    widgets.make_label(board, 'Mục tiêu / công việc · %', bold=True, padx=10).grid(
        row=0, column=0, sticky='nsew')
    state.calendar_header = tk.Canvas(board, height=timeline.HEADER_HEIGHT, bg=WHITE, highlightthickness=0)
    state.calendar_header.grid(row=0, column=1, sticky='ew')
    state.calendar_names = tk.Canvas(board, width=timeline.NAME_WIDTH, height=230,
                                     bg=WHITE, highlightthickness=0)
    state.calendar_names.grid(row=1, column=0, sticky='ns')
    state.calendar_canvas = tk.Canvas(board, height=230, bg=WHITE, highlightthickness=0,
                                      xscrollincrement=timeline.DAY_WIDTH, yscrollincrement=timeline.ROW_HEIGHT)
    state.calendar_canvas.grid(row=1, column=1, sticky='nsew')
    horizontal = ttk.Scrollbar(board, orient='horizontal', command=cuon_ngang)
    horizontal.grid(row=2, column=1, sticky='ew')
    vertical = ttk.Scrollbar(board, command=cuon_doc)
    vertical.grid(row=1, column=2, sticky='ns')

    def sync_x(first, last):
        horizontal.set(first, last)
        state.calendar_header.xview_moveto(first)
        timeline.draw_grid()

    def sync_y(first, last):
        vertical.set(first, last)
        state.calendar_names.yview_moveto(first)

    state.calendar_canvas.configure(xscrollcommand=sync_x, yscrollcommand=sync_y)
    state.calendar_canvas.bind('<Configure>', lambda event: timeline.draw_grid())
    state.calendar_header.bind('<Button-1>', chon_o_ngay)
    for canvas in (state.calendar_names, state.calendar_canvas, state.calendar_header):
        canvas.bind('<MouseWheel>', cuon_chuot)

    widgets.make_label(
        state.under_frame_3,
        'Nền nhạt: thời gian dự kiến · Dải xanh: tiến độ task · % dưới ngày: tỷ lệ task lá đã xong',
        size=9, color=MUTED, bg=BG,
    ).grid(row=2, column=0, sticky='w', pady=4)
    selection = tk.Frame(state.under_frame_3, bg=BG)
    selection.grid(row=3, column=0, sticky='ew')
    widgets.make_label(selection, textvariable=state.calendar_selection_text,
                       bg=BG, size=9, color=BLUE, wraplength=500).pack(side='left')
    calendar_button(selection, 'Sửa', sua_task_tren_lich).pack(side='right')
    calendar_button(selection, '+ Việc con', them_task_con).pack(side='right', padx=4)
    calendar_button(selection, 'Mở chi tiết', mo_chi_tiet).pack(side='right')

    detail = tk.Frame(state.under_frame_3, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    detail.grid(row=4, column=0, sticky='ew', pady=(6, 0))
    filters = tk.Frame(detail, bg=WHITE)
    filters.pack(fill='x', padx=10, pady=6)
    mode = ttk.Combobox(filters, values=('Ngày', 'Tuần', 'Chưa xếp lịch'),
                         textvariable=state.calendar_mode, state='readonly', width=16)
    mode.pack(side='left')
    mode.bind('<<ComboboxSelected>>', lambda event: chon_ngay(state.selected_day))
    ttk.Checkbutton(filters, text='Cả việc đã xong', variable=state.calendar_include_done,
                    command=lambda: chon_ngay(state.selected_day)).pack(side='left', padx=12)
    calendar_button(filters, '+ Công việc', lambda: forms.mo_form_cong_viec(
        planned_date=None if state.calendar_mode.get() == 'Chưa xếp lịch' else state.selected_day,
    )).pack(side='right')
    calendar_button(filters, 'Xong', lambda: actions.danh_dau_hoan_thanh(state.day_task_list)).pack(side='right')
    calendar_button(filters, 'Sửa', lambda: actions.sua_viec_da_chon(state.day_task_list)).pack(side='right')
    state.day_title = tk.StringVar(state.window)
    state.day_summary = tk.StringVar(state.window)
    widgets.make_label(detail, textvariable=state.day_title, size=10, bold=True).pack(anchor='w', padx=10)
    state.day_task_list = widgets.tao_bang(detail, (
        ('name', 'Việc cần làm', 260), ('project', 'Mục tiêu', 170),
        ('due', 'Hạn hoàn thành', 110), ('status', 'Trạng thái', 110),
    ), height=1, expand=False)
    style = ttk.Style(state.window)
    style.configure('Calendar.Treeview', rowheight=26, font=('Segoe UI', 9))
    style.configure('Calendar.Treeview.Heading', font=('Segoe UI', 9), padding=(5, 4))
    state.day_task_list.configure(style='Calendar.Treeview')
    state.day_task_list.bind('<Double-1>', lambda event: actions.sua_viec_da_chon(state.day_task_list))
    state.day_task_list.bind('<Return>', lambda event: actions.sua_viec_da_chon(state.day_task_list))
    state.under_frame_3.bind('<Configure>', doi_kich_thuoc_lich)
    ve_cac_ngay()


def doi_kich_thuoc_lich(event):
    # Cửa sổ thấp vẫn dành chỗ cho lịch; bảng luôn có thanh cuộn.
    height = 1 if event.height < 430 else (2 if event.height < 520 else 3)
    if int(state.day_task_list['height']) != height:
        state.day_task_list.configure(height=height)


def cuon_ngang(*args):
    state.calendar_canvas.xview(*args)


def cuon_doc(*args):
    state.calendar_canvas.yview(*args)


def cuon_chuot(event):
    units = -1 if event.delta > 0 else 1
    if event.state & 1:  # Shift + cuộn chuột để dịch lịch ngang.
        cuon_ngang('scroll', units * 3, 'units')
    else:
        cuon_doc('scroll', units, 'units')
    return 'break'


def cap_nhat_lich_tuan():
    """Tên cũ, nhưng tải lại toàn bộ cây mục tiêu và mọi khoảng thời gian."""
    try:
        tasks = calendar_data.load_calendar_tasks()
    except sqlite3.Error as error:
        messagebox.showerror('Không thể tải lịch', data.database_error_message(error), parent=state.window)
        return False
    state.calendar_tasks = tasks
    ids = {task['id'] for task in tasks}
    state.calendar_collapsed.intersection_update(ids)
    if state.calendar_selected_task not in ids:
        state.calendar_selected_task = None
    ve_cac_ngay()
    return True


def ve_cac_ngay():
    timeline.draw(chon_task, thu_gon, lambda task_id: forms.mo_form_cong_viec(task_id=task_id))
    state.week_title.set(f'{state.calendar_start:%d/%m/%Y} – {state.calendar_end:%d/%m/%Y}')
    cap_nhat_task_dang_chon()
    cap_nhat_danh_sach()


def cap_nhat_task_dang_chon():
    task = next((task for task in state.calendar_tasks if task['id'] == state.calendar_selected_task), None)
    if task:
        state.calendar_selection_text.set(
            f"{task['title']} · {data.display_date(task['start_date'])} → "
            f"{data.display_date(task['end_date'])} · {task['progress']:.1f}%")
    else:
        state.calendar_selection_text.set('Chọn một mục tiêu trên lịch để thao tác.')


def chon_task(task_id):
    state.calendar_selected_task = task_id
    ve_cac_ngay()


def thu_gon(task_id):
    if task_id in state.calendar_collapsed:
        state.calendar_collapsed.remove(task_id)
    else:
        state.calendar_collapsed.add(task_id)
    ve_cac_ngay()


def chon_o_ngay(event):
    offset = int(state.calendar_header.canvasx(event.x) // timeline.DAY_WIDTH)
    if 0 <= offset < state.calendar_days:
        chon_ngay(state.calendar_start + timedelta(days=offset))


def chon_ngay(day):
    state.selected_day = day
    state.week_start = day - timedelta(days=day.weekday())
    if not state.calendar_start <= day <= state.calendar_end:
        ve_cac_ngay()
    else:
        timeline.draw_grid()
        cap_nhat_danh_sach()
    timeline.scroll_to_day(day)


def cap_nhat_danh_sach():
    mode = state.calendar_mode.get()
    day = state.selected_day
    title = 'Chưa xếp lịch — task lá thiếu ngày hoặc có khoảng ngày không hợp lệ'
    if mode == 'Ngày':
        title = f'Việc trong ngày {day:%d/%m/%Y}'
    elif mode == 'Tuần':
        start = day - timedelta(days=day.weekday())
        end = start + timedelta(days=6)
        title = f'Việc trong tuần {start:%d/%m/%Y} – {end:%d/%m/%Y}'
    tasks = calendar_data.tasks_for_period(
        state.calendar_tasks, day, mode, state.calendar_include_done.get())
    state.day_summary.set(f'{len(tasks)} công việc · Chỉ liệt kê task lá')
    state.day_title.set(f'{title} · {len(tasks)} task lá')
    tree = state.day_task_list
    selected = tree.selection()
    tree.delete(*tree.get_children())
    for task in tasks:
        tree.insert('', 'end', iid=str(task['id']), tags=(task['status'],), values=(
            task['title'], task['project_name'], data.display_date(task['end_date']), task['status'],
        ))
    if selected and tree.exists(selected[0]):
        tree.selection_set(selected[0])


def chuyen_tuan(offset):
    chon_ngay(state.selected_day + timedelta(weeks=offset))


def ve_tuan_hien_tai():
    chon_ngay(date.today())


def task_da_chon():
    task_id = state.calendar_selected_task
    if task_id is None:
        messagebox.showinfo('Chọn mục tiêu', 'Hãy chọn một mục tiêu hoặc công việc trên lịch.', parent=state.window)
    return task_id


def them_task_con():
    task_id = task_da_chon()
    if task_id is not None:
        forms.mo_form_cong_viec(project_id=task_id)


def sua_task_tren_lich():
    task_id = task_da_chon()
    if task_id is not None:
        forms.mo_form_cong_viec(task_id=task_id)


def mo_chi_tiet():
    task_id = task_da_chon()
    if task_id is not None and actions.show_sample(task_id):
        actions.show_frame1()
