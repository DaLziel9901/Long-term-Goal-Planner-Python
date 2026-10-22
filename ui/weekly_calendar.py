"""Điều phối lịch heatmap và danh sách công việc."""

import sqlite3
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from ui import actions, calendar_data, data, forms, state, timeline, widgets
from ui.widgets import BG, BLUE, BORDER, LIGHT_BLUE, MUTED, WHITE

MIN_HEATMAP_HEIGHT = timeline.GRID_HEIGHT + timeline.HEADER_HEIGHT + 50


def calendar_button(parent, text, command, primary=False):
    return widgets.make_button(parent, text, command, primary, compact=True)


def tao_trang_lich():
    state.selected_day = date.today()
    state.week_start = state.selected_day - timedelta(days=state.selected_day.weekday())
    state.calendar_tasks = []
    state.window.today_status_job = None
    state.window.bind('<Destroy>', huy_cap_nhat_thong_tin_hom_nay, add='+')
    cap_nhat_thong_tin_hom_nay()
    state.calendar_scope_tasks = []
    state.calendar_selected_task = None
    state.calendar_mode = tk.StringVar(state.window, 'Tuần')
    state.calendar_include_done = tk.BooleanVar(state.window, False)
    state.calendar_split_initialized = False
    state.calendar_compact = None
    state.calendar_task_ids = [None]
    state.calendar_progress_text = tk.StringVar(state.window, '')
    state.calendar_selection_text = tk.StringVar(state.window)
    state.week_title = tk.StringVar(state.window)
    state.under_frame_3.columnconfigure(0, weight=1)
    state.under_frame_3.rowconfigure(1, weight=1)

    toolbar = tk.Frame(state.under_frame_3, bg=BG)
    toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 6))
    heading_icon = widgets.make_icon_image(state.window, 'calendar', size=22, gap=6)
    heading = widgets.make_label(toolbar, 'Lịch mục tiêu', size=12, bold=True, bg=BG,
                                  image=heading_icon, compound='left')
    heading.image = heading_icon
    heading.pack(side='left', padx=(0, 12))
    calendar_button(toolbar, '+ Mục tiêu', forms.open_add_project, True).pack(side='left')
    calendar_button(toolbar, 'Hôm nay', ve_tuan_hien_tai).pack(side='right')
    calendar_button(toolbar, 'Tháng sau ›', lambda: chuyen_thang(1)).pack(side='right', padx=4)
    calendar_button(toolbar, '‹ Tháng trước', lambda: chuyen_thang(-1)).pack(side='right')

    state.calendar_panes = tk.PanedWindow(
        state.under_frame_3, orient='vertical', bg=BG, borderwidth=0,
        sashwidth=10, sashrelief='flat', showhandle=False, sashcursor='sb_v_double_arrow', opaqueresize=True,
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
    horizontal = widgets.AutoScrollbar(board, orient='horizontal', command=cuon_ngang,
                                      style='Calendar.Horizontal.TScrollbar')
    horizontal.grid(row=2, column=1, sticky='ew')

    def sync_x(first, last):
        horizontal.set(first, last)
        state.calendar_header.xview_moveto(first)
        timeline.draw_grid()

    state.calendar_canvas.configure(xscrollcommand=sync_x)
    state.calendar_canvas.bind('<Configure>', lambda event: timeline.draw_grid())
    state.calendar_canvas.bind('<Button-1>', chon_o_ngay)
    for canvas in (state.calendar_canvas, state.calendar_header):
        canvas.bind('<MouseWheel>', cuon_chuot)

    selection = tk.Frame(state.calendar_upper, bg=WHITE, padx=10, pady=1,
                         highlightbackground=BORDER, highlightthickness=1)
    selection.grid(row=1, column=0, sticky='ew', pady=(4, 0))
    selection.columnconfigure(0, weight=1)
    scope = tk.Frame(selection, bg=WHITE)
    scope.grid(row=0, column=0, sticky='w')
    widgets.make_label(scope, 'Mục tiêu', color=MUTED, size=9).pack(side='left', padx=(0, 10))
    state.calendar_target = ttk.Combobox(scope, values=('Tất cả mục tiêu',),
                                        state='readonly', width=28, style='Calendar.TCombobox')
    state.calendar_target.current(0)
    state.calendar_target.pack(side='left')
    state.calendar_target.bind('<<ComboboxSelected>>', chon_muc_tieu)
    widgets.make_label(scope, textvariable=state.calendar_progress_text,
                       size=9, color=BLUE).pack(side='left', padx=8)
    goal_actions = tk.Frame(selection, bg=WHITE)
    goal_actions.grid(row=0, column=1, sticky='e', padx=(10, 0))
    calendar_button(goal_actions, 'Mở chi tiết', mo_chi_tiet).pack(side='left', padx=(0, 4))
    calendar_button(goal_actions, '+ Việc con', them_task_con).pack(side='left', padx=(0, 4))
    calendar_button(goal_actions, 'Sửa', sua_task_tren_lich).pack(side='left')
    for button in goal_actions.winfo_children():
        button.configure(height=30, font=('Segoe UI', 9), padx=10)

    detail = tk.Frame(state.calendar_panes, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    state.calendar_detail = detail
    state.calendar_panes.add(detail, minsize=150, stretch='always')
    filters = tk.Frame(detail, bg=WHITE)
    state.calendar_filter_bar = filters
    filters.pack(fill='x', padx=10, pady=(5, 3))
    filters.columnconfigure(1, weight=1)
    mode_group = widgets.RoundedPanel(filters)
    mode_group.grid(row=0, column=0, sticky='w')
    state.calendar_mode_buttons = {}
    for name in ('Ngày', 'Tuần', 'Chưa xếp lịch'):
        button = widgets.make_button(mode_group.content, name, lambda value=name: chon_che_do(value),
                                     variant='nav', compact=True)
        button.configure(font=('Segoe UI Semibold', 9), padx=8, height=30)
        button.pack(side='left', padx=1)
        state.calendar_mode_buttons[name] = button
    state.calendar_mode.trace_add('write', cap_nhat_nut_che_do)
    cap_nhat_nut_che_do()
    ttk.Checkbutton(filters, text='Cả việc đã xong', variable=state.calendar_include_done,
                    style='Calendar.TCheckbutton', command=lambda: chon_ngay(state.selected_day)).grid(
                        row=0, column=1, sticky='w', padx=10)
    task_actions = tk.Frame(filters, bg=WHITE)
    state.calendar_task_actions = task_actions
    task_actions.grid(row=0, column=2, sticky='e')
    calendar_button(task_actions, 'Sửa', lambda: actions.sua_viec_da_chon(state.day_task_list)).pack(side='left')
    calendar_button(task_actions, 'Xong', lambda: actions.danh_dau_hoan_thanh(state.day_task_list)).pack(side='left', padx=4)
    calendar_button(task_actions, '+ Công việc', lambda: forms.mo_form_cong_viec(
        planned_date=None if state.calendar_mode.get() == 'Chưa xếp lịch' else state.selected_day,
    ), True).pack(side='left')
    state.day_title = tk.StringVar(state.window)
    state.day_summary = tk.StringVar(state.window)
    heading = tk.Frame(detail, bg=WHITE)
    state.calendar_list_heading = heading
    heading.pack(fill='x', padx=14, pady=(1, 6))
    count = widgets.make_label(heading, textvariable=state.day_summary, size=9, color=BLUE,
                               bg=LIGHT_BLUE, padx=8, pady=2)
    count.pack(side='right', padx=(12, 0))
    state.calendar_count_label = count
    title = widgets.make_label(heading, textvariable=state.day_title, size=9, bold=True)
    title.pack(side='left', fill='x', expand=True)
    heading.bind('<Configure>', lambda event: title.configure(wraplength=max(120, event.width - count.winfo_reqwidth() - 20)))
    table_area = tk.Frame(detail, bg=WHITE)
    state.calendar_table_area = table_area
    table_area.pack(fill='both', expand=True, padx=8, pady=(0, 6))
    state.day_task_list = widgets.tao_bang(table_area, (
        ('project', 'Mục tiêu', 160), ('due', 'Hạn hoàn thành', 116), ('status', 'Trạng thái', 112),
    ), height=4, expand=True, style='Calendar.Treeview', auto_scroll=True)
    state.day_task_list.configure(show='tree headings')
    state.day_task_list.heading('#0', text='Việc cần làm', anchor='w')
    state.day_task_list.column('#0', width=300, minwidth=190, stretch=True)
    for column in ('project', 'due', 'status'):
        state.day_task_list.column(column, stretch=False)
    state.day_task_list.tag_configure('calendar_group', background='#F0F4FA', foreground='#64758C',
                                      font=('Segoe UI Semibold', 9))
    state.day_task_list.tag_configure('calendar_even', background=WHITE)
    state.day_task_list.tag_configure('calendar_odd', background='#FAFBFD')
    state.day_task_list.tag_configure('calendar_done', foreground=MUTED)
    state.calendar_empty_label = widgets.make_label(state.day_task_list,
        'Không có công việc trong phạm vi này.', size=10, color=MUTED)
    state.day_task_list.bind('<Double-1>', sua_viec_trong_bang)
    state.day_task_list.bind('<Return>', sua_viec_trong_bang)
    state.calendar_panes.bind('<Configure>', doi_kich_thuoc_lich)
    ve_cac_ngay()


def cap_nhat_nut_che_do(*args):
    for name, button in state.calendar_mode_buttons.items():
        button.configure(selected=name == state.calendar_mode.get())


def chon_che_do(mode):
    state.calendar_mode.set(mode)
    chon_ngay(state.selected_day)


def doi_kich_thuoc_lich(event):
    compact = event.height < 500
    if state.calendar_compact != compact:
        state.calendar_compact = compact
        style = ttk.Style(state.window)
        style.configure('Calendar.Treeview', rowheight=26 if compact else 32)
        style.configure('Calendar.Treeview.Heading', padding=(10, 3 if compact else 7))
        for button in state.calendar_mode_buttons.values():
            button.configure(height=24 if compact else 30)
        for button in state.calendar_task_actions.winfo_children():
            family = 'Segoe UI Semibold' if button.cget('variant') == 'primary' else 'Segoe UI'
            button.configure(height=28 if compact else None,
                             font=(family, 9 if compact else 10))
        state.calendar_filter_bar.pack_configure(pady=(1, 1) if compact else (5, 3))
        state.calendar_list_heading.pack_configure(pady=(0, 2) if compact else (1, 6))
        state.calendar_count_label.configure(pady=0 if compact else 2)
        state.calendar_table_area.pack_configure(pady=(0, 2) if compact else (0, 6))
    if not state.calendar_split_initialized and event.height > 350:
        state.calendar_panes.sash_place(0, 0, max(MIN_HEATMAP_HEIGHT, int(event.height * 0.58)))
        state.calendar_split_initialized = True


def cuon_ngang(*args):
    state.calendar_canvas.xview(*args)


def cuon_chuot(event):
    units = -1 if event.delta > 0 else 1
    cuon_ngang('scroll', units * 3, 'units')
    return 'break'


def cap_nhat_thong_tin_hom_nay():
    """Đếm task lá của hôm nay trên mọi mục tiêu, kể cả việc đã xong."""
    state.window.today_status_job = None
    today = date.today()
    tasks = calendar_data.tasks_for_period(state.calendar_tasks, today, 'Ngày', True)
    done = sum(task['is_done'] == 1 for task in tasks)
    total = len(tasks)
    state.status_text.set(
        f'Hôm nay: {today:%d/%m/%Y} | Tổng: {total} công việc | '
        f'Đã xong: {done} | Chưa xong: {total - done}')


def huy_cap_nhat_thong_tin_hom_nay(event):
    if event.widget is state.window and state.window.today_status_job is not None:
        state.window.after_cancel(state.window.today_status_job)
        state.window.today_status_job = None


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
    # Hiện tổng kết sau khi callback thêm/sửa/xóa đã ghi thông báo thao tác.
    if state.window.today_status_job is not None:
        state.window.after_cancel(state.window.today_status_job)
    state.window.today_status_job = state.window.after_idle(cap_nhat_thong_tin_hom_nay)
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
    state.day_title.set(title)
    tree = state.day_task_list
    selected = tree.selection()
    opened = {group: tree.item(group, 'open') for group in tree.get_children()}
    tree.delete(*tree.get_children())
    groups = {}
    for group, text in (('scheduled', 'Đã xếp lịch'), ('unscheduled', 'Chưa xếp lịch')):
        if any(task['scheduled'] == (group == 'scheduled') for task in tasks):
            count = sum(task['scheduled'] == (group == 'scheduled') for task in tasks)
            groups[group] = tree.insert('', 'end', iid=group, text=f'{text}  ·  {count}',
                                        tags=('calendar_group',), open=opened.get(group, True))
    for index, task in enumerate(tasks):
        group = 'scheduled' if task['scheduled'] else 'unscheduled'
        tags = ('calendar_even' if index % 2 == 0 else 'calendar_odd',)
        if task['status'] == 'Hoàn thành':
            tags += ('calendar_done',)
        tree.insert(groups[group], 'end', iid=str(task['id']), text=task['title'], tags=tags, values=(
            task['project_name'],
            data.display_date(task['end_date']) if task['scheduled'] else 'Chưa xếp lịch', task['status'],
        ))
    if selected and tree.exists(selected[0]):
        tree.selection_set(selected[0])
    if tasks:
        state.calendar_empty_label.place_forget()
    else:
        state.calendar_empty_label.place(relx=0.5, rely=0.6, anchor='center')


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
