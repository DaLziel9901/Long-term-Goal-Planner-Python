"""Màu sắc, style và các widget dùng chung."""


import tkinter as tk
from tkinter import ttk


BG = '#F4F5F7'
WHITE = '#FFFFFF'
TEXT = '#273343'
MUTED = '#707B89'
BLUE = '#3869B8'
BLUE_HOVER = '#2B5598'
LIGHT_BLUE = '#EBF0F8'
BORDER = '#E1E5EB'
SOFT = '#F8F9FB'
MAU_TRANG_THAI = {'Chưa làm': '#8A6A36', 'Đang làm': BLUE, 'Hoàn thành': '#39806A'}
NEN_TRANG_THAI = {'Chưa làm': '#F7F3EA', 'Đang làm': LIGHT_BLUE, 'Hoàn thành': '#EAF4EF'}
TEN_THU = ('Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ nhật')


def make_label(parent, text='', size=10, color=TEXT, bold=False, bg=WHITE, **options):
    return tk.Label(parent,
        text=text,
        bg=bg,
        fg=color,
        anchor='w',
        justify='left',
        font=('Segoe UI', size, 'bold' if bold else 'normal'),
        **options)


def make_button(parent, text, command, primary=False):
    """Nút dùng chung có màu khi rê chuột, luôn gắn hành động thực tế."""
    base = BLUE if primary else WHITE
    hover = BLUE_HOVER if primary else LIGHT_BLUE
    button = tk.Button(parent,
        text=text,
        command=command,
        bg=base,
        fg=WHITE if primary else TEXT,
        activebackground=hover,
        activeforeground=WHITE if primary else BLUE,
        relief='flat',
        bd=0,
        cursor='hand2',
        padx=16,
        pady=11,
        font=('Segoe UI', 10, 'bold'),
        takefocus=True)
    button.bind('<Enter>', lambda event: button.configure(bg=hover))
    button.bind('<Leave>', lambda event: button.configure(bg=base))
    return button


def tao_bang(parent, columns, height=6, expand=True):
    """Bảng có thanh cuộn; mỗi cột gồm tên trong code, nhãn và chiều rộng."""
    frame = tk.Frame(parent, bg=WHITE)
    frame.pack(fill='both' if expand else 'x', expand=expand)
    tree = ttk.Treeview(frame,
        columns=[column[0] for column in columns],
        show='headings',
        selectmode='browse',
        height=height,
        style='Task.Treeview')
    for index, (key, label, width) in enumerate(columns):
        tree.heading(key, text=label, anchor='w')
        tree.column(key, width=width, minwidth=70, stretch=index == 0)
    vertical = ttk.Scrollbar(frame, command=tree.yview, style='Slim.Vertical.TScrollbar')
    horizontal = ttk.Scrollbar(frame,
        orient='horizontal',
        command=tree.xview,
        style='Slim.Horizontal.TScrollbar')
    tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    tree.grid(row=0, column=0, sticky='nsew')
    vertical.grid(row=0, column=1, sticky='ns')
    horizontal.grid(row=1, column=0, sticky='ew')
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    for status, color in MAU_TRANG_THAI.items():
        tree.tag_configure(status, foreground=color)
    return tree


def configure_styles(window):
    """Cấu hình màu sắc, font và style ttk dùng chung."""
    style = ttk.Style(window)
    style.theme_use('clam')
    style.configure('Project.Treeview',
        background=WHITE,
        fieldbackground=WHITE,
        foreground=TEXT,
        rowheight=46,
        borderwidth=0,
        font=('Segoe UI', 11),
        lightcolor=WHITE,
        darkcolor=WHITE)
    style.layout('Project.Treeview', [('Treeview.treearea', {'sticky': 'nswe'})])
    style.map('Project.Treeview', background=[('selected', LIGHT_BLUE)], foreground=[('selected', BLUE)])
    style.configure('Task.Treeview',
        background=WHITE,
        fieldbackground=WHITE,
        foreground=TEXT,
        rowheight=34,
        borderwidth=0,
        font=('Segoe UI', 10))
    style.configure('Task.Treeview.Heading',
        background=SOFT,
        foreground=MUTED,
        relief='flat',
        font=('Segoe UI', 9),
        padding=(8, 9))
    style.map('Task.Treeview', background=[('selected', LIGHT_BLUE)], foreground=[('selected', TEXT)])
    style.configure('Form.TCombobox', padding=(8, 7), fieldbackground=SOFT, foreground=TEXT)
    for key, status in (('todo', 'Chưa làm'), ('doing', 'Đang làm'), ('done', 'Hoàn thành')):
        style.configure(f'{key}.Horizontal.TProgressbar',
            background=MAU_TRANG_THAI[status],
            troughcolor='#EDF0F4',
            bordercolor='#EDF0F4',
            borderwidth=0,
            lightcolor=MAU_TRANG_THAI[status],
            darkcolor=MAU_TRANG_THAI[status],
            thickness=7)
    style.configure('Form.TEntry',
        padding=(10, 9),
        fieldbackground=SOFT,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER)
    style.map('Form.TEntry', bordercolor=[('focus', BLUE)], lightcolor=[('focus', BLUE)])
    style.configure('TScrollbar',
        background=BORDER,
        troughcolor=WHITE,
        borderwidth=0,
        arrowsize=12,
        lightcolor=WHITE,
        darkcolor=WHITE)
    for direction, sticky in (('Vertical', 'ns'), ('Horizontal', 'we')):
        name = f'Slim.{direction}.TScrollbar'
        style.layout(name,
            [(f'{direction}.Scrollbar.trough', {'sticky': sticky, 'children': [(f'{direction}.Scrollbar.thumb', {'expand': True, 'sticky': 'nswe'})]})])
        style.configure(name,
            background='#D4DEEC',
            troughcolor=SOFT,
            borderwidth=0,
            lightcolor='#D4DEEC',
            darkcolor='#D4DEEC',
            arrowsize=8,
            gripcount=0)
        style.map(name, background=[('active', '#B4C5DF'), ('pressed', '#9BB3D8')])
