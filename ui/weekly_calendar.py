"""Điều phối lịch heatmap và danh sách việc; giữ tên module để dùng callback cũ."""

import sqlite3
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from ui import actions, calendar_data, data, forms, state, timeline, widgets
from ui.widgets import BG, BLUE, BORDER, WHITE

MIN_HEATMAP_HEIGHT = timeline.GRID_HEIGHT + timeline.HEADER_HEIGHT + 48


def calendar_button(parent, text, command, primary=False):
    button = widgets.make_button(parent, text, command, primary)
    button.configure(pady=5, padx=10)
    return button


def tao_trang_lich():
    state.selected_day = date.today()
    state.week_start = state.selected_day - timedelta(days=state.selected_day.weekday())
    state.calendar_tasks = []
    state.calendar_scope_tasks = []
    state.calendar_selected_task = None
    state.calendar_mode = tk.StringVar(state.window, 'Tuần')
    state.calendar_include_done = tk.BooleanVar(state.window, False)
    state.calendar_split_initialized = False
    state.calendar_task_ids = [None]
    state.calendar_progress_text = tk.StringVar(state.window, '')
    state.calendar_selection_text = tk.StringVar(state.window)
    state.week_title = tk.StringVar(state.window)
    state.under_frame_3.columnconfigure(0, weight=1)
    state.under_frame_3.rowconfigure(1, weight=1)

    toolbar = tk.Frame(state.under_frame_3, bg=BG)
    toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 6))
    calendar_button(toolbar, '+ Mục tiêu', forms.open_add_project, True).pack(side='left')
    calendar_button(toolbar, 'Hôm nay', ve_tuan_hien_tai).pack(side='right')
    calendar_button(toolbar, 'Tháng sau ›', lambda: chuyen_thang(1)).pack(side='right', padx=4)
    calendar_button(toolbar, '‹ Tháng trước', lambda: chuyen_thang(-1)).pack(side='right')

    state.calendar_panes = tk.PanedWindow(
        state.under_frame_3, orient='vertical', bg=BORDER, borderwidth=0,
        sashwidth=8, sashrelief='flat', showhandle=True, handlesize=10, opaqueresize=True,
    )
    state.calendar_panes.grid(row=1, column=0, sticky='nsew')
    state.calendar_upper = tk.Frame(state.calendar_panes, bg=BG)
    state.calendar_upper.columnconfigure(0, weight=1)
    state.calendar_upper.rowconfigure(0, weight=1)
    state.calendar_panes.add(state.calendar_upper, minsize=MIN_HEATMAP_HEIGHT, stretch='always')
    board = tk.Frame(state.calendar_upper, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    board.grid(row=0, column=0, sticky='nsew')
    board.columnconfigure(1, weight=1)
    board.rowconfigure(1, weight=1)
    state.calendar_header = tk.Canvas(board, height=timeline.HEADER_HEIGHT, bg=WHITE, highlightthickness=0)
    state.calendar_header.grid(row=0, column=1, sticky='ew')
    state.calendar_names = tk.Canvas(board, width=timeline.NAME_WIDTH, height=timeline.GRID_HEIGHT,
                                     bg=WHITE, highlightthickness=0)
    state.calendar_names.grid(row=1, column=0, sticky='ns')
    state.calendar_canvas = tk.Canvas(board, height=timeline.GRID_HEIGHT, bg=WHITE,
                                      highlightthickness=0, xscrollincrement=timeline.CELL_STEP)
    state.calendar_canvas.grid(row=1, column=1, sticky='nsew')
    horizontal = ttk.Scrollbar(board, orient='horizontal', command=cuon_ngang,
                               style='Slim.Horizontal.TScrollbar')
    horizontal.grid(row=2, column=1, sticky='ew')

    def sync_x(first, last):
        horizontal.set(first, last)
        state.calendar_header.xview_moveto(first)
        timeline.draw_grid()

    state.calendar_canvas.configure(xscrollcommand=sync_x)
    state.calendar_canvas.bind('<Configure>', lambda event: timeline.draw_grid())
    state.calendar_canvas.bind('<Button-1>', chon_o_ngay)
    state.calendar_canvas.bind('<Motion>', thong_tin_o_ngay)
    for canvas in (state.calendar_canvas, state.calendar_header):
        canvas.bind('<MouseWheel>', cuon_chuot)

    selection = tk.Frame(state.calendar_upper, bg=BG)
    selection.grid(row=1, column=0, sticky='ew', pady=(4, 0))
    widgets.make_label(selection, 'Mục tiêu', bg=BG, size=9).pack(side='left', padx=(0, 6))
    state.calendar_target = ttk.Combobox(selection, values=('Tất cả mục tiêu',),
                                        state='readonly', width=28)
    state.calendar_target.current(0)
    state.calendar_target.pack(side='left')
    state.calendar_target.bind('<<ComboboxSelected>>', chon_muc_tieu)
    widgets.make_label(selection, textvariable=state.calendar_progress_text,
                       bg=BG, size=9, color=BLUE).pack(side='left', padx=8)
    calendar_button(selection, 'Sửa', sua_task_tren_lich).pack(side='right')
    calendar_button(selection, '+ Việc con', them_task_con).pack(side='right', padx=4)
    calendar_button(selection, 'Mở chi tiết', mo_chi_tiet).pack(side='right')

    detail = tk.Frame(state.calendar_panes, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    state.calendar_detail = detail
    state.calendar_panes.add(detail, minsize=130, stretch='always')
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
    ), height=4, expand=True)
    style = ttk.Style(state.window)
    style.configure('Calendar.Treeview', rowheight=26, font=('Segoe UI', 9))
    style.configure('Calendar.Treeview.Heading', font=('Segoe UI', 9), padding=(5, 4))
    state.day_task_list.configure(style='Calendar.Treeview')
    state.day_task_list.configure(show='tree headings')
    state.day_task_list.heading('#0', text='Nhóm')
    state.day_task_list.column('#0', width=130, minwidth=100, stretch=False)
    state.day_task_list.bind('<Double-1>', sua_viec_trong_bang)
    state.day_task_list.bind('<Return>', sua_viec_trong_bang)
    state.calendar_panes.bind('<Configure>', doi_kich_thuoc_lich)
    ve_cac_ngay()


def doi_kich_thuoc_lich(event):
    if not state.calendar_split_initialized and event.height > 350:
        state.calendar_panes.sash_place(0, 0, max(MIN_HEATMAP_HEIGHT, int(event.height * 0.58)))
        state.calendar_split_initialized = True


def cuon_ngang(*args):
    state.calendar_canvas.xview(*args)


def cuon_chuot(event):
    units = -1 if event.delta > 0 else 1
    cuon_ngang('scroll', units * 3, 'units')
    return 'break'


def cap_nhat_lich_tuan():
    """Sau khi lưu: đọc lại dữ liệu, giữ mục tiêu đang chọn nếu nó còn tồn tại."""
    try:
        tasks = calendar_data.load_calendar_tasks()
    except sqlite3.Error as error:
        messagebox.showerror('Không thể tải lịch', data.database_error_message(error), parent=state.window)
        return False
    state.calendar_tasks = tasks
    scheduled = [task for task in tasks if task['scheduled']]
    state.calendar_task_ids = [None] + [task['id'] for task in scheduled]
    state.calendar_target.configure(values=['Tất cả mục tiêu'] + [
        '  ' * min(task['level'], 4) + task['title'] for task in scheduled
    ])
    if state.calendar_selected_task not in state.calendar_task_ids:
        state.calendar_selected_task = None
    state.calendar_target.current(state.calendar_task_ids.index(state.calendar_selected_task))
    ve_cac_ngay()
    return True


def ve_cac_ngay():
    state.calendar_scope_tasks = calendar_data.tasks_in_scope(state.calendar_tasks, state.calendar_selected_task)
    timeline.draw_heatmap()
    state.week_title.set(f'{state.calendar_start:%d/%m/%Y} – {state.calendar_end:%d/%m/%Y}')
    cap_nhat_task_dang_chon()
    cap_nhat_danh_sach()


def cap_nhat_task_dang_chon():
    task = next((task for task in state.calendar_tasks if task['id'] == state.calendar_selected_task), None)
    if task:
        state.calendar_selection_text.set(
            f"{task['title']} · {data.display_date(task['start_date'])} → "
            f"{data.display_date(task['end_date'])} · {task['progress']:.1f}%")
        state.calendar_progress_text.set(f"{task['progress']:.0f}%")
    else:
        state.calendar_selection_text.set('Tất cả mục tiêu')
        state.calendar_progress_text.set('')


def chon_task(task_id):
    state.calendar_selected_task = task_id if task_id in state.calendar_task_ids else None
    state.calendar_target.current(state.calendar_task_ids.index(state.calendar_selected_task))
    ve_cac_ngay()
    task = next((task for task in state.calendar_tasks if task['id'] == task_id), None)
    if task and task['scheduled']:
        chon_ngay(task['calendar_start'])
    state.status_text.set(state.calendar_selection_text.get())


def chon_muc_tieu(event=None):
    index = state.calendar_target.current()
    if 0 <= index < len(state.calendar_task_ids):
        chon_task(state.calendar_task_ids[index])


def chon_o_ngay(event):
    day = timeline.day_at(state.calendar_canvas.canvasx(event.x), state.calendar_canvas.canvasy(event.y))
    if day is not None:
        if state.calendar_mode.get() == 'Chưa xếp lịch':
            state.calendar_mode.set('Ngày')
        chon_ngay(day)


def thong_tin_o_ngay(event):
    day = timeline.day_at(state.calendar_canvas.canvasx(event.x), state.calendar_canvas.canvasy(event.y))
    if day is None:
        return
    leaves = calendar_data.tasks_for_period(state.calendar_scope_tasks, day, 'Ngày', True)
    percent = calendar_data.day_completion(state.calendar_scope_tasks, day)
    progress = 'Chưa có việc được lên lịch' if percent is None else f'{percent:.0f}% hoàn thành'
    state.status_text.set(f'{day:%d/%m/%Y} · {len(leaves)} công việc · {progress}')


def chon_ngay(day):
    state.selected_day = day
    state.week_start = day - timedelta(days=day.weekday())
    if not state.calendar_start <= day <= state.calendar_end:
        timeline.draw_heatmap()
    else:
        timeline.draw_grid()
    cap_nhat_danh_sach()
    timeline.scroll_to_day(day)


def chuyen_thang(offset):
    chon_ngay(calendar_data.shift_month(state.selected_day, offset))

def cap_nhat_danh_sach():
    mode = state.calendar_mode.get()
    day = state.selected_day
    title = 'Chưa xếp lịch — task thiếu ngày hoặc có khoảng ngày không hợp lệ'
    if mode == 'Ngày':
        title = f'Việc trong ngày {day:%d/%m/%Y}'
    elif mode == 'Tuần':
        start = day - timedelta(days=day.weekday())
        end = start + timedelta(days=6)
        title = f'Tuần {start:%d/%m/%Y} – {end:%d/%m/%Y} (kèm việc chưa xếp lịch)'
    tasks = calendar_data.tasks_for_period(
        state.calendar_scope_tasks, day, mode, state.calendar_include_done.get())
    state.day_summary.set(f'{len(tasks)} mục')
    state.day_title.set(f'{title} · {len(tasks)} mục')
    tree = state.day_task_list
    selected = tree.selection()
    opened = {group: tree.item(group, 'open') for group in tree.get_children()}
    tree.delete(*tree.get_children())
    groups = {}
    for group, text in (('scheduled', 'Đã xếp lịch'), ('unscheduled', 'Chưa xếp lịch')):
        if any(task['scheduled'] == (group == 'scheduled') for task in tasks):
            groups[group] = tree.insert('', 'end', iid=group, text=text,
                                        open=opened.get(group, True))
    for task in tasks:
        group = 'scheduled' if task['scheduled'] else 'unscheduled'
        tree.insert(groups[group], 'end', iid=str(task['id']), tags=(task['status'],), values=(
            task['title'], task['project_name'],
            data.display_date(task['end_date']) if task['scheduled'] else 'Chưa xếp lịch', task['status'],
        ))
    if selected and tree.exists(selected[0]):
        tree.selection_set(selected[0])


def sua_viec_trong_bang(event=None):
    selected = state.day_task_list.selection()
    if selected and selected[0].isdigit():
        actions.sua_viec_da_chon(state.day_task_list)


def chuyen_tuan(offset):
    chon_ngay(state.selected_day + timedelta(weeks=offset))


def ve_tuan_hien_tai():
    chon_ngay(date.today())


def task_da_chon():
    task_id = state.calendar_selected_task
    if task_id is None:
        messagebox.showinfo('Chọn mục tiêu', 'Hãy chọn một mục tiêu hoặc công việc ở ô chọn phía trên.', parent=state.window)
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
