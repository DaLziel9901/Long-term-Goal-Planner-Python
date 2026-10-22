import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from ui import calendar_data, state, widgets
from ui.widgets import BORDER, MUTED, TEXT, WHITE

DONE_COLOR = '#39806A'
PENDING_COLOR = '#D7DEE8'


def build_chart(parent):
    today = date.today()
    state.stats_chart_week = today - timedelta(days=today.weekday())
    state.stats_chart_goal = None
    state.stats_chart_tasks = []
    state.stats_chart_goal_ids = [None]
    state.stats_chart_week_text = tk.StringVar(state.window)

    toolbar = tk.Frame(parent, bg=WHITE)
    toolbar.pack(fill='x', padx=12, pady=8)
    navigation = tk.Frame(toolbar, bg=WHITE)
    navigation.pack(fill='x')
    widgets.make_label(navigation, textvariable=state.stats_chart_week_text,
                       size=10, bold=True).pack(side='left')
    scope = tk.Frame(toolbar, bg=WHITE)
    scope.pack(fill='x', pady=(6, 0))
    widgets.make_label(scope, 'Mục tiêu', size=9).pack(side='left', padx=(0, 6))
    state.stats_chart_goal_combo = ttk.Combobox(
        scope, values=('Tất cả mục tiêu',), state='readonly', width=24,
    )
    state.stats_chart_goal_combo.current(0)
    state.stats_chart_goal_combo.pack(side='left')
    state.stats_chart_goal_combo.bind('<<ComboboxSelected>>', select_goal)
    for text, command in (('›', lambda: change_week(1)),
                          ('Tuần này', current_week), ('‹', lambda: change_week(-1))):
        button = widgets.make_button(navigation, text, command, compact=True)
        button.pack(side='right', padx=2)

    note = widgets.make_label(
        parent,
        'Chỉ tính task lá có đủ ngày. Một task kéo dài có thể được tính ở nhiều ngày.\n'
        'Biểu đồ phản ánh trạng thái hiện tại của kế hoạch, chưa phải lịch sử hoàn thành.',
        size=9, color=MUTED,
    )
    note.pack(side='bottom', fill='x', padx=12, pady=(0, 8))
    note.bind('<Configure>', lambda event: note.configure(wraplength=max(100, event.width)))
    state.stats_chart_figure = Figure(figsize=(8, 3.2), dpi=100, facecolor=WHITE)
    state.stats_chart_axes = state.stats_chart_figure.add_subplot(111)
    state.stats_chart_figure.subplots_adjust(left=0.08, right=0.98, bottom=0.21, top=0.83)
    state.stats_chart_canvas = FigureCanvasTkAgg(state.stats_chart_figure, master=parent)
    state.stats_chart_canvas.get_tk_widget().pack(fill='both', expand=True)
    render_chart()


def refresh_chart(tasks):
    """Giữ tuần và mục tiêu đang xem khi CRUD làm dữ liệu thay đổi."""
    state.stats_chart_tasks = tasks
    state.stats_chart_goal_ids = [None] + [task['id'] for task in tasks]
    state.stats_chart_goal_combo.configure(values=['Tất cả mục tiêu'] + [
        '  ' * min(task['level'], 4) + task['title'] for task in tasks
    ])
    if state.stats_chart_goal not in state.stats_chart_goal_ids:
        state.stats_chart_goal = None
    state.stats_chart_goal_combo.current(state.stats_chart_goal_ids.index(state.stats_chart_goal))
    render_chart()


def render_chart():
    tasks = calendar_data.tasks_in_scope(state.stats_chart_tasks, state.stats_chart_goal)
    counts = calendar_data.weekly_counts(tasks, state.stats_chart_week)
    state.stats_chart_counts = counts
    first, last = counts[0]['day'], counts[-1]['day']
    state.stats_chart_week_text.set(f'{first:%d/%m/%Y} – {last:%d/%m/%Y}')
    axes = state.stats_chart_axes
    axes.clear()
    days = list(range(7))
    done = [item['done'] for item in counts]
    pending = [item['pending'] for item in counts]
    axes.bar(days, done, color=DONE_COLOR, width=0.6, label='Đã xong')
    axes.bar(days, pending, bottom=done, color=PENDING_COLOR, width=0.6, label='Chưa xong')
    names = ('T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN')
    axes.set_xticks(days, [f"{name}\n{item['day']:%d/%m}" for name, item in zip(names, counts)])
    axes.set_ylabel('Số tasks', color=TEXT, fontsize=9)
    maximum = max(1, max(item['total'] for item in counts))
    axes.set_ylim(0, maximum * 1.35)
    axes.yaxis.set_major_locator(MaxNLocator(integer=True, min_n_ticks=2))
    axes.tick_params(axis='both', labelsize=9, colors=TEXT)
    axes.set_axisbelow(True)
    axes.grid(axis='y', color=BORDER, linewidth=0.7)
    for side in ('top', 'right'):
        axes.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        axes.spines[side].set_color(BORDER)
    for index, item in enumerate(counts):
        label = ('Không có\nviệc' if item['total'] == 0 else
                 f"{item['done']}/{item['total']} · {item['progress']:.0f}%")
        axes.text(index, item['total'] + maximum * 0.04, label,
                  ha='center', va='bottom', fontsize=8, color=MUTED if not item['total'] else TEXT)
    axes.legend(loc='upper center', bbox_to_anchor=(0.5, 1.18), ncol=2, frameon=False, fontsize=9)
    state.stats_chart_canvas.draw()


def change_week(offset):
    state.stats_chart_week += timedelta(weeks=offset)
    render_chart()


def current_week():
    today = date.today()
    state.stats_chart_week = today - timedelta(days=today.weekday())
    render_chart()


def select_goal(event=None):
    index = state.stats_chart_goal_combo.current()
    if 0 <= index < len(state.stats_chart_goal_ids):
        state.stats_chart_goal = state.stats_chart_goal_ids[index]
        render_chart()
