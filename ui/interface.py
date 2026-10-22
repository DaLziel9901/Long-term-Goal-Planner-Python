"""Dựng bố cục cửa sổ; khởi động ứng dụng bằng python main.py."""


import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk
from ui import actions, forms, state, statistics, weekly_calendar, widgets
from ui.widgets import (BG, BLUE, BORDER, LIGHT_BLUE, MUTED, TEXT, WHITE)


def build_interface():
    state.task_dialog, state.add_dialog, state.selected_project_id = (None, None, None)
    state.window = tk.Tk()
    state.window.title('Lịch dài hạn')
    state.window.geometry('1140x780')
    state.window.minsize(860, 600)
    state.window.configure(bg=BG)
    state.window.option_add('*Font', ('Segoe UI', 10))
    widgets.configure_styles(state.window)
    state.taskbar = tk.Frame(state.window, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
    state.taskbar.pack(fill='x')
    brand = tk.Frame(state.taskbar, bg=WHITE)
    brand.pack(side='left', padx=(28, 30), pady=18)
    logo_path = Path(__file__).resolve().parent / 'assets' / 'logo.png'
    with Image.open(logo_path) as source:
        logo_image = ImageTk.PhotoImage(
            source.convert('RGBA').resize((36, 36), Image.Resampling.LANCZOS),
            master=state.window,
        )
    logo_label = tk.Label(brand, image=logo_image, bg=WHITE, bd=0, padx=0, pady=0)
    logo_label.image = logo_image
    logo_label.pack(side='left', padx=(0, 10))
    state.title1 = widgets.make_label(brand, 'Lịch dài hạn', 15, TEXT, True)
    state.title1.pack(side='left')
    navigation = widgets.RoundedPanel(state.taskbar)
    navigation.pack(side='left', pady=12)
    state.button1 = widgets.make_button(navigation.content, 'Kế hoạch', actions.show_frame1, variant='nav', icon='list')
    state.button2 = widgets.make_button(navigation.content, 'Thống kê', actions.show_frame2, variant='nav', icon='chart')
    state.button3 = widgets.make_button(navigation.content, 'Lịch mục tiêu', actions.show_frame3, variant='nav', icon='calendar')
    for button in (state.button1, state.button2, state.button3):
        button.pack(side='left', padx=1)
    state.page_title_icons = {
        name: widgets.make_icon_image(state.window, name, size=32, gap=10)
        for name in ('list', 'chart', 'calendar')
    }
    state.page_title = tk.StringVar(state.window)
    state.page_subtitle = tk.StringVar(state.window)
    introduction = tk.Frame(state.window, bg=BG)
    introduction.pack(fill='x', padx=28, pady=(18, 16))
    state.firstSay = widgets.make_label(introduction,
        size=21,
        bold=True,
        bg=BG,
        compound='left',
        textvariable=state.page_title)
    state.firstSay.pack(anchor='w')
    widgets.make_label(introduction,
        color=MUTED,
        bg=BG,
        textvariable=state.page_subtitle).pack(anchor='w',
        padx=(42, 0),
        pady=(5, 0))
    state.status_text = tk.StringVar(state.window, 'Sẵn sàng')
    widgets.make_label(state.window,
        size=9,
        color=MUTED,
        bg=BG,
        textvariable=state.status_text).pack(side='bottom',
        fill='x',
        padx=30,
        pady=(0, 12))
    state.under_frame_1 = tk.Frame(state.window, bg=BG)
    state.under_frame_2 = tk.Frame(state.window, bg=BG)
    state.under_frame_3 = tk.Frame(state.window, bg=BG)
    state.project_frame = tk.Frame(state.under_frame_1,
        bg=WHITE,
        width=230,
        highlightbackground=BORDER,
        highlightthickness=1)
    state.project_frame.pack(side='left', fill='y', padx=(0, 18))
    state.project_frame.pack_propagate(False)
    state.contentbar = tk.Frame(state.under_frame_1,
        bg=WHITE,
        highlightbackground=BORDER,
        highlightthickness=1)
    state.contentbar.pack(side='left', fill='both', expand=True)
    sidebar_heading = tk.Frame(state.project_frame, bg=WHITE)
    sidebar_heading.pack(fill='x', padx=18, pady=(22, 8))
    state.title2 = widgets.make_label(sidebar_heading, 'Mục tiêu', 13, TEXT, True)
    state.title2.pack(side='left')
    state.project_count = tk.StringVar(state.window, '0')
    widgets.make_label(sidebar_heading,
        color=BLUE,
        bold=True,
        bg=LIGHT_BLUE,
        textvariable=state.project_count,
        padx=8,
        pady=2).pack(side='right')
    widgets.make_label(state.project_frame,
        'Danh sách mục tiêu',
        9,
        MUTED).pack(anchor='w',
        padx=18,
        pady=(0, 14))
    footer = tk.Frame(state.project_frame, bg=WHITE)
    footer.pack(side='bottom', fill='x', padx=16, pady=16)
    state.button_add = widgets.make_button(footer, '+ Thêm mục tiêu', actions.show_project, primary=True)
    state.button_add.pack(fill='x')
    state.button_delete = widgets.make_button(footer, 'Xóa mục tiêu', actions.xoa_du_an_dang_chon,
                                               variant='danger', compact=True)
    state.button_delete.pack(fill='x', pady=(6, 0))
    tk.Frame(state.project_frame, bg=BORDER, height=1).pack(side='bottom', fill='x', padx=16)
    list_frame = tk.Frame(state.project_frame, bg=WHITE)
    list_frame.pack(fill='both', expand=True, padx=10, pady=(0, 12))
    state.project_list = ttk.Treeview(list_frame, show='tree', selectmode='browse', style='Project.Treeview')
    vertical = ttk.Scrollbar(list_frame,
        orient='vertical',
        command=state.project_list.yview,
        style='Slim.Vertical.TScrollbar')
    horizontal = ttk.Scrollbar(list_frame,
        orient='horizontal',
        command=state.project_list.xview,
        style='Slim.Horizontal.TScrollbar')
    state.project_list.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    list_frame.rowconfigure(0, weight=1)
    list_frame.columnconfigure(0, weight=1)
    state.project_list.grid(row=0, column=0, sticky='nsew')
    vertical.grid(row=0, column=1, sticky='ns')
    horizontal.grid(row=1, column=0, sticky='ew')
    state.project_list.bind('<<TreeviewSelect>>', actions.select_project)
    state.content_canvas = tk.Canvas(state.contentbar, bg=WHITE, highlightthickness=0, yscrollincrement=20)
    content_scroll = ttk.Scrollbar(state.contentbar,
        command=state.content_canvas.yview,
        style='Slim.Vertical.TScrollbar')
    state.content_canvas.configure(yscrollcommand=content_scroll.set)
    content_scroll.pack(side='right', fill='y')
    state.content_canvas.pack(side='left', fill='both', expand=True)
    state.content_inner = tk.Frame(state.content_canvas, bg=WHITE, padx=24, pady=20)
    state.content_window = state.content_canvas.create_window((0, 0), window=state.content_inner, anchor='nw')
    state.content_inner.bind('<Configure>',
        lambda event: state.content_canvas.configure(scrollregion=state.content_canvas.bbox('all')))
    state.content_canvas.bind('<Configure>', actions.resize_content)
    state.window.bind('<MouseWheel>', actions.scroll_content)
    state.content_title = tk.StringVar(state.window)
    state.content_description = tk.StringVar(state.window)
    state.start_text = tk.StringVar(state.window)
    state.end_text = tk.StringVar(state.window)
    state.project_badge = tk.StringVar(state.window)
    state.project_heading = widgets.make_label(state.content_inner,
        size=21,
        bold=True,
        textvariable=state.content_title)
    state.project_heading.pack(fill='x', pady=(0, 5))
    detail_actions = tk.Frame(state.content_inner, bg=WHITE)
    detail_actions.pack(fill='x')
    widgets.make_button(detail_actions, 'Về mục trước', actions.ve_task_cha, compact=True).pack(side='left', padx=(0, 6))
    widgets.make_button(detail_actions, 'Sửa mục này', actions.sua_task_hien_tai, compact=True).pack(side='left', padx=(0, 6))
    widgets.make_button(detail_actions, 'Đổi hoàn thành', actions.doi_trang_thai_hien_tai, compact=True).pack(side='left')
    tk.Frame(state.content_inner, bg=BORDER, height=1).pack(fill='x', pady=10)
    date_cards = tk.Frame(state.content_inner, bg=WHITE)
    date_cards.pack(fill='x')
    date_cards.columnconfigure((0, 1), weight=1, uniform='date_cards')
    for column, caption, value in ((0, 'Bắt đầu', state.start_text), (1, 'Kết thúc', state.end_text)):
        card = tk.Frame(date_cards, bg=WHITE, pady=4)
        card.grid(row=0, column=column, sticky='nsew', padx=(0, 6) if column == 0 else (6, 0))
        widgets.make_label(card, caption, 9, MUTED).pack(anchor='w')
        widgets.make_label(card, size=11, textvariable=value).pack(anchor='w', pady=(4, 0))
    state.description_label = widgets.make_label(state.content_inner,
        size=10,
        color=MUTED,
        textvariable=state.content_description)
    state.description_label.pack(fill='x', pady=(10, 12))
    state.project_progress_text = tk.StringVar(state.window)
    widgets.make_label(state.content_inner,
        size=9,
        color=MUTED,
        textvariable=state.project_progress_text).pack(anchor='w',
        pady=(0, 7))
    state.project_progress = ttk.Progressbar(state.content_inner,
        maximum=100,
        style='doing.Horizontal.TProgressbar')
    state.project_progress.pack(fill='x')
    tk.Frame(state.content_inner, bg=BORDER, height=1).pack(fill='x', pady=12)
    heading = tk.Frame(state.content_inner, bg=WHITE)
    heading.pack(fill='x', pady=(0, 8))
    widgets.make_label(heading, 'Công việc', 12, bold=True).pack(side='left')
    add_task_button = widgets.make_button(heading,
        '+ Công việc',
        lambda: forms.mo_form_cong_viec(project_id=state.selected_project_id),
        True, compact=True)
    add_task_button.pack(side='right')
    state.empty_label = widgets.make_label(state.content_inner, color=MUTED, size=9)
    state.empty_label.pack(fill='x', pady=(0, 6))
    state.task_list = widgets.tao_bang(state.content_inner,
        (('name', 'Công việc', 260), ('planned', 'Dự kiến', 100), ('due', 'Hạn', 100), ('status', 'Trạng thái', 110)),
        height=5,
        expand=False)
    state.task_list.bind('<Double-1>', lambda event: actions.mo_viec_da_chon())
    state.task_list.bind('<Return>', lambda event: actions.mo_viec_da_chon())
    action_bar = tk.Frame(state.content_inner, bg=WHITE)
    action_bar.pack(fill='x', pady=(8, 0))
    widgets.make_button(action_bar, 'Mở', actions.mo_viec_da_chon).pack(side='left', padx=(0, 6))
    widgets.make_button(action_bar,
        'Sửa',
        lambda: actions.sua_viec_da_chon(state.task_list)).pack(side='left', padx=(0, 6))
    widgets.make_button(action_bar,
        'Xóa',
        lambda: actions.xoa_viec_da_chon(state.task_list), variant='danger').pack(side='left')
    widgets.make_button(action_bar,
        'Đánh dấu xong',
        lambda: actions.danh_dau_hoan_thanh(state.task_list)).pack(side='right')
    statistics.tao_trang_thong_ke()
    weekly_calendar.tao_trang_lich()
    actions.show_empty_project()
    actions.show_frame1()
    return state.window


def main():
    """Giữ lệnh chạy cũ: python -m ui.interface."""
    from main import main as run_app
    return run_app()


if __name__ == "__main__":
    main()
