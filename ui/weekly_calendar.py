"""Dựng và cập nhật lịch tuần."""


import sqlite3
import tkinter as tk
from datetime import date
from datetime import timedelta
from tkinter import messagebox
from ui import actions, data, forms, state, widgets
from ui.widgets import (BG, BLUE, BORDER, MAU_TRANG_THAI, MUTED, NEN_TRANG_THAI, TEN_THU, TEXT, WHITE)


def tao_trang_lich():
    state.selected_day = date.today()
    state.week_start = state.selected_day - timedelta(days=state.selected_day.weekday())
    state.week_columns, state.week_tasks_by_day = ({}, {})
    state.week_card_limit = 2
    state.week_title = tk.StringVar(state.window)
    toolbar = tk.Frame(state.under_frame_3, bg=BG)
    toolbar.pack(fill='x', pady=(0, 12))
    widgets.make_label(toolbar, size=14, bold=True, bg=BG, textvariable=state.week_title).pack(side='left')
    next_button = widgets.make_button(toolbar, 'Tuần sau ›', lambda: chuyen_tuan(1))
    today_button = widgets.make_button(toolbar, 'Hôm nay', ve_tuan_hien_tai)
    prev_button = widgets.make_button(toolbar, '‹ Tuần trước', lambda: chuyen_tuan(-1))
    for button in (next_button, today_button, prev_button):
        button.configure(pady=8)
        button.pack(side='right', padx=(6, 0))
    state.week_board = tk.Frame(state.under_frame_3, bg=BORDER, height=210)
    state.week_board.pack(fill='x')
    state.week_board.pack_propagate(False)
    state.week_board.grid_propagate(False)
    state.week_board.rowconfigure(0, weight=1)
    for column in range(7):
        state.week_board.columnconfigure(column, weight=1, uniform='week')
    legend = tk.Frame(state.under_frame_3, bg=BG)
    legend.pack(fill='x', pady=(6, 8))
    for status, color in MAU_TRANG_THAI.items():
        widgets.make_label(legend, f'●  {status}', 9, color, bg=BG).pack(side='left', padx=(0, 18))
    detail = tk.Frame(state.under_frame_3, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    detail.pack(fill='both', expand=True)
    heading = tk.Frame(detail, bg=WHITE)
    heading.pack(fill='x', padx=16, pady=8)
    state.day_title, state.day_summary = (tk.StringVar(state.window), tk.StringVar(state.window))
    widgets.make_label(heading, size=11, bold=True, textvariable=state.day_title).pack(side='left')
    widgets.make_label(heading,
        size=9,
        color=MUTED,
        textvariable=state.day_summary).pack(side='left',
        padx=12)
    add_button = widgets.make_button(heading,
        '+ Công việc',
        lambda: forms.mo_form_cong_viec(planned_date=state.selected_day),
        True)
    add_button.configure(pady=6)
    add_button.pack(side='right')
    state.day_task_list = widgets.tao_bang(detail,
        (('name', 'Công việc', 310), ('project', 'Dự án', 190), ('due', 'Hạn hoàn thành', 120), ('status', 'Trạng thái', 120)),
        height=4)
    state.day_task_list.bind('<Double-1>', lambda event: actions.sua_viec_da_chon(state.day_task_list))
    state.day_task_list.bind('<Return>', lambda event: actions.sua_viec_da_chon(state.day_task_list))
    state.under_frame_3.bind('<Configure>', doi_kich_thuoc_lich)


def doi_kich_thuoc_lich(event):
    """Ưu tiên chừa chỗ cho bảng chi tiết khi thu thấp cửa sổ."""
    height = min(220, max(140, event.height // 2 - 50))
    state.week_board.configure(height=height)
    limit = 1 if height < 185 else 2
    if limit != state.week_card_limit:
        state.week_card_limit = limit
        if state.week_tasks_by_day:
            ve_cac_ngay()


def cap_nhat_lich_tuan():
    """Xếp công việc theo ngày dự kiến, giữ việc không có ngày ở trang Kế hoạch."""
    try:
        tasks = data.cong_viec_trong_tuan(state.week_start)
    except sqlite3.Error as error:
        messagebox.showerror('Không thể tải lịch', data.database_error_message(error), parent=state.window)
        return False
    end = state.week_start + timedelta(days=6)
    state.week_title.set(f'{state.week_start:%d/%m/%Y} – {end:%d/%m/%Y}')
    state.week_tasks_by_day = {state.week_start + timedelta(days=offset): [] for offset in range(7)}
    for task in tasks:
        day = date.fromisoformat(task['planned_date'])
        state.week_tasks_by_day[day].append(task)
    ve_cac_ngay()
    return True


def ve_cac_ngay():
    """Vẽ lại bảy cột từ dữ liệu đã đọc, không truy vấn lại khi co cửa sổ."""
    for widget in state.week_board.winfo_children():
        widget.destroy()
    state.week_columns = {}
    for column, (day, day_tasks) in enumerate(state.week_tasks_by_day.items()):
        frame = tk.Frame(state.week_board, bg=WHITE, highlightthickness=1, highlightbackground=BORDER)
        frame.grid(row=0, column=column, sticky='nsew', padx=(0, 1) if column < 6 else 0)
        frame.grid_propagate(False)
        state.week_columns[day] = frame
        header = tk.Frame(frame, bg=WHITE)
        header.pack(fill='x', padx=10, pady=(8, 4))
        widgets.make_label(header, TEN_THU[day.weekday()], 9, MUTED).pack(anchor='w')
        widgets.make_label(header,
            f'{day.day:02d}',
            18,
            BLUE if day == date.today() else TEXT,
            True).pack(anchor='w')
        for widget in (frame, header, *header.winfo_children()):
            widget.bind('<Button-1>', lambda event, chosen=day: chon_ngay(chosen))
        for task in day_tasks[:state.week_card_limit]:
            block = tk.Frame(frame, bg=NEN_TRANG_THAI[task['status']], padx=7, pady=4)
            block.pack(fill='x', padx=6, pady=(0, 5))
            name = task['name'] if len(task['name']) <= 45 else task['name'][:44] + '…'
            label = widgets.make_label(block, name, 9, MAU_TRANG_THAI[task['status']], bg=block['bg'])
            label.configure(height=2, anchor='nw')
            label.pack(fill='x')
            block.bind('<Configure>',
                lambda event,
                text=label: text.configure(wraplength=max(40, event.width - 14)))
            for widget in (block, label):
                widget.bind('<Button-1>',
                    lambda event,
                    chosen=day,
                    task_id=task['id']: chon_viec_tren_lich(chosen, task_id))
                widget.bind('<Double-1>',
                    lambda event,
                    task_id=task['id']: forms.mo_form_cong_viec(task_id=task_id))
        if len(day_tasks) > state.week_card_limit:
            more = widgets.make_label(frame, f'+{len(day_tasks) - state.week_card_limit} việc khác', 9, MUTED)
            more.pack(anchor='w', padx=10)
            more.bind('<Button-1>', lambda event, chosen=day: chon_ngay(chosen))
    if state.selected_day not in state.week_columns:
        state.selected_day = state.week_start
    chon_ngay(state.selected_day)


def chon_ngay(day):
    previous_day, previous_week = (state.selected_day, state.week_start)
    state.selected_day = day
    if day not in state.week_columns:
        state.week_start = day - timedelta(days=day.weekday())
        if not cap_nhat_lich_tuan():
            state.selected_day, state.week_start = (previous_day, previous_week)
        return
    for current, frame in state.week_columns.items():
        frame.configure(highlightbackground=BLUE if current == day else BORDER,
            highlightthickness=2 if current == day else 1)
    state.day_title.set(f'{TEN_THU[day.weekday()]}, {day:%d/%m/%Y}')
    tasks = state.week_tasks_by_day.get(day, [])
    state.day_summary.set(f'{len(tasks)} công việc' if tasks else 'Chưa có công việc')
    selection = state.day_task_list.selection()
    items = state.day_task_list.get_children()
    if items:
        state.day_task_list.delete(*items)
    for task in tasks:
        state.day_task_list.insert('',
            'end',
            iid=str(task['id']),
            tags=(task['status'],),
            values=(task['name'], task['project_name'], data.display_date(task['due_date']), task['status']))
    if selection and state.day_task_list.exists(selection[0]):
        state.day_task_list.selection_set(selection[0])


def chon_viec_tren_lich(day, task_id):
    chon_ngay(day)
    state.day_task_list.selection_set(str(task_id))
    state.day_task_list.see(str(task_id))


def chuyen_tuan(offset):
    previous_week, previous_day = (state.week_start, state.selected_day)
    state.week_start += timedelta(weeks=offset)
    state.selected_day += timedelta(weeks=offset)
    if not cap_nhat_lich_tuan():
        state.week_start, state.selected_day = (previous_week, previous_day)


def ve_tuan_hien_tai():
    previous_week, previous_day = (state.week_start, state.selected_day)
    state.selected_day = date.today()
    state.week_start = state.selected_day - timedelta(days=state.selected_day.weekday())
    if not cap_nhat_lich_tuan():
        state.week_start, state.selected_day = (previous_week, previous_day)
