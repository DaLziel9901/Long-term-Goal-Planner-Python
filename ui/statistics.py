"""Dựng và cập nhật trang thống kê."""


import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from ui import calendar_data, data, state, weekly_chart, widgets
from ui.widgets import (BG, BLUE, BORDER, MAU_TRANG_THAI, MUTED, TEXT, WHITE)


def tao_trang_thong_ke():
    state.stats_values, state.stats_progress = ({}, {})
    state.stats_tabs = ttk.Notebook(state.under_frame_2)
    state.stats_tabs.pack(fill='both', expand=True)
    chart = tk.Frame(state.stats_tabs, bg=WHITE)
    overview = tk.Frame(state.stats_tabs, bg=BG)
    state.stats_tabs.add(chart, text='Biểu đồ tuần')
    state.stats_tabs.add(overview, text='Tổng quan')
    weekly_chart.build_chart(chart)
    numbers = tk.Frame(overview, bg=BG)
    numbers.pack(fill='x', pady=(0, 16))
    for column, (key,
        caption) in enumerate((('projects', 'Mục tiêu'), ('total', 'Công việc'), ('done', 'Hoàn thành'), ('pending', 'Chưa xong'), ('progress', 'Tỷ lệ hoàn thành'))):
        numbers.columnconfigure(column, weight=1, uniform='numbers')
        card = tk.Frame(numbers, bg=WHITE, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=14)
        card.grid(row=0, column=column, sticky='nsew', padx=(0, 10) if column < 4 else 0)
        widgets.make_label(card, caption, 10, MUTED).pack(anchor='w')
        state.stats_values[key] = tk.StringVar(state.window, '0%' if key == 'progress' else '0')
        widgets.make_label(card,
            size=25,
            color=BLUE if key == 'progress' else TEXT,
            bold=True,
            textvariable=state.stats_values[key]).pack(anchor='w',
            pady=(8, 0))
    bottom = tk.Frame(overview, bg=BG)
    bottom.pack(fill='both', expand=True)
    left = tk.Frame(bottom, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    left.pack(side='left', fill='both', expand=True, padx=(0, 16))
    widgets.make_label(left, 'Tiến độ theo mục tiêu', 13, bold=True).pack(anchor='w', padx=20, pady=18)
    state.stats_canvas = tk.Canvas(left, bg=WHITE, highlightthickness=0, yscrollincrement=20)
    scroll = ttk.Scrollbar(left, command=state.stats_canvas.yview, style='Slim.Vertical.TScrollbar')
    state.stats_canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right', fill='y')
    state.stats_canvas.pack(fill='both', expand=True)
    state.stats_rows = tk.Frame(state.stats_canvas, bg=WHITE, padx=20)
    item = state.stats_canvas.create_window((0, 0), window=state.stats_rows, anchor='nw')
    state.stats_rows.bind('<Configure>',
        lambda event: state.stats_canvas.configure(scrollregion=state.stats_canvas.bbox('all')))
    state.stats_canvas.bind('<Configure>',
        lambda event: state.stats_canvas.itemconfigure(item, width=event.width))
    right = tk.Frame(bottom, bg=WHITE, width=254, highlightbackground=BORDER, highlightthickness=1)
    right.pack(side='right', fill='y')
    right.pack_propagate(False)
    widgets.make_label(right, 'Trạng thái công việc', 12, bold=True).pack(anchor='w', padx=20, pady=12)
    state.stats_status_values, state.stats_status_bars = ({}, {})
    for key, caption in (('todo', 'Chưa làm'), ('doing', 'Đang làm'), ('done', 'Hoàn thành')):
        row = tk.Frame(right, bg=WHITE)
        row.pack(fill='x', padx=20, pady=(0, 3))
        widgets.make_label(row, caption, color=MAU_TRANG_THAI[caption]).pack(side='left')
        state.stats_status_values[key] = tk.StringVar(state.window, '0')
        widgets.make_label(row, textvariable=state.stats_status_values[key], bold=True).pack(side='right')
        bar = ttk.Progressbar(right, maximum=100, style=f'{key}.Horizontal.TProgressbar')
        bar.pack(fill='x', padx=20, pady=(0, 8))
        state.stats_status_bars[key] = bar
    tk.Frame(right, bg=BORDER, height=1).pack(fill='x', padx=20, pady=(0, 8))
    late = tk.Frame(right, bg=WHITE)
    late.pack(fill='x', padx=20)
    widgets.make_label(late, 'Quá hạn', color='#A6524C').pack(side='left')
    state.stats_status_values['overdue'] = tk.StringVar(state.window, '0')
    widgets.make_label(late,
        color='#A6524C',
        bold=True,
        textvariable=state.stats_status_values['overdue']).pack(side='right')


def cap_nhat_thong_ke():
    try:
        summary = data.thong_ke_tong_quan()
        projects = data.thong_ke_du_an()
        tasks = calendar_data.load_calendar_tasks()
    except sqlite3.Error as error:
        messagebox.showerror('Không thể tải thống kê',
            data.database_error_message(error),
            parent=state.window)
        return False
    for key, variable in state.stats_values.items():
        variable.set(f'{summary[key]:g}%' if key == 'progress' else str(summary[key]))
    for key, variable in state.stats_status_values.items():
        variable.set(str(summary[key]))
        if key in state.stats_status_bars:
            state.stats_status_bars[key].configure(value=summary[key] * 100 / summary['total'] if summary['total'] else 0)
    position = state.stats_canvas.yview()[0]
    for widget in state.stats_rows.winfo_children():
        widget.destroy()
    state.stats_progress = {}
    if not projects:
        widgets.make_label(state.stats_rows,
            'Chưa có dự án để thống kê.',
            color=MUTED).pack(anchor='w',
            pady=12)
    for project in projects:
        row = tk.Frame(state.stats_rows, bg=WHITE)
        row.pack(fill='x', pady=(2, 18))
        heading = tk.Frame(row, bg=WHITE)
        heading.pack(fill='x', pady=(0, 10))
        heading.columnconfigure(0, weight=1)
        label = widgets.make_label(heading, project['name'], 11, bold=True)
        label.grid(row=0, column=0, sticky='w')
        heading.bind('<Configure>',
            lambda event,
            text=label: text.configure(wraplength=max(80, event.width - 145)))
        widgets.make_label(heading,
            f"{project['done']}/{project['total']} · {project['progress']:g}%",
            10,
            MUTED).grid(row=0,
            column=1,
            sticky='e',
            padx=(12, 0))
        bar = ttk.Progressbar(row,
            maximum=100,
            value=project['progress'],
            style='doing.Horizontal.TProgressbar')
        bar.pack(fill='x')
        state.stats_progress[project['id']] = bar
        widgets.make_label(row,
            f"{project['pending']} công việc chưa xong",
            9,
            MUTED).pack(anchor='w',
            pady=(6, 0))
    state.stats_canvas.update_idletasks()
    state.stats_canvas.yview_moveto(position)
    weekly_chart.refresh_chart(tasks)
    return True
