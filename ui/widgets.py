"""Màu sắc, style và các widget dùng chung."""


import tkinter as tk
import tkinter.font as tkfont
import time
from functools import lru_cache
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

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


class RoundedButton(tk.Canvas):
    """Nút có cạnh khử răng cưa, chuyển màu theo thời gian và hỗ trợ bàn phím."""

    def __init__(self, parent, text, command, variant='secondary', compact=False, icon=None):
        emphasis = variant in ('primary', 'nav')
        self._button_options = dict(text=text, command=command, variant=variant,
                                    state='normal', selected=False, padx=12 if compact else 16,
                                    pady=5 if compact else 8,
                                    font=('Segoe UI Semibold' if emphasis else 'Segoe UI', 10),
                                    width=None, height=None, icon=icon)
        self._hover = self._mouse_down = self._focused = False
        self._pointer_focus = self._focus_visible = False
        self._key_down = None
        self._animation = None
        self._current = self._target = None
        self._photo = None
        super().__init__(parent, bg=parent.cget('bg'), highlightthickness=0,
                         bd=0, takefocus=1, cursor='hand2')
        self._surface = self.create_image(0, 0, anchor='nw')
        self._caption = self.create_text(0, 0)
        self._resize()
        self.bind('<Configure>', self._draw)
        self.bind('<Enter>', lambda event: self._set_hover(True))
        self.bind('<Leave>', lambda event: self._set_hover(False))
        self.bind('<ButtonPress-1>', self._press)
        self.bind('<ButtonRelease-1>', self._release)
        self.bind('<FocusIn>', lambda event: self._set_focus(True))
        self.bind('<FocusOut>', lambda event: self._set_focus(False))
        for key in ('space', 'Return'):
            self.bind(f'<KeyPress-{key}>', self._key_press)
            self.bind(f'<KeyRelease-{key}>', self._key_release)
        self.bind('<Escape>', self._cancel_press)
        self.bind('<Destroy>', self._cleanup)
        self._refresh(animate=False)

    def configure(self, cnf=None, **options):
        if isinstance(cnf, dict):
            options = {**cnf, **options}
        elif cnf is not None:
            return super().configure(cnf, **options)
        if not options:
            return super().configure()
        custom = {key: options.pop(key) for key in tuple(options) if key in self._button_options}
        self._button_options.update(custom)
        if options:
            super().configure(**options)
        if custom:
            if any(key in custom for key in ('text', 'font', 'padx', 'pady', 'width', 'height', 'icon')):
                self._resize()
            if self._button_options['state'] == 'disabled':
                self._mouse_down, self._key_down = False, None
            super().configure(cursor='arrow' if self._button_options['state'] == 'disabled' else 'hand2',
                              takefocus=0 if self._button_options['state'] == 'disabled' else 1)
            self._refresh()

    config = configure

    def cget(self, key):
        return self._button_options[key] if key in self._button_options else super().cget(key)

    __getitem__ = cget

    def invoke(self):
        if self._button_options['state'] != 'disabled' and self._button_options['command'] is not None:
            return self._button_options['command']()

    def focus_keyboard(self):
        """Hiện dấu focus khi chuyển bằng bàn phím, tách khỏi thao tác chuột."""
        self._pointer_focus = False
        self._focus_visible = True
        self.focus_set()
        self._refresh()

    def _resize(self):
        self._font = tkfont.Font(self, font=self._button_options['font'])
        label = self._button_options['text']
        if self._button_options['icon'] == 'plus':
            label = label.lstrip('+ ')
        self._icon_size = max(14, round(self._font.metrics('linespace') * 0.8))
        self._icon_space = self._icon_size + 7 if self._button_options['icon'] else 0
        self._content_width = self._font.measure(label) + self._icon_space
        width = self._button_options['width'] or self._content_width + 2 * self._button_options['padx'] + 8
        height = self._button_options['height'] or self._font.metrics('linespace') + 2 * self._button_options['pady'] + 8
        super().configure(width=width, height=height)
        self.itemconfigure(self._caption, text=label, font=self._font)
        self._draw()

    def _draw(self, event=None):
        if self._current is not None:
            self._paint()

    def _palette(self):
        background = self.cget('bg')
        if self._button_options['state'] == 'disabled':
            return '#EFF2F6', '#E8EDF3', '#9BA6B5', background, background, 0
        variant = self._button_options['variant']
        pressed = bool(self._key_down or (self._mouse_down and self._hover))
        shadow = background
        if variant == 'primary':
            base, hover, down, border, text = BLUE, '#305FA9', '#294F8C', BLUE, WHITE
            shadow = '#CFDAEB' if self._hover else '#DFE6F0'
        elif variant == 'danger':
            base, hover, down, border, text = '#FFF8F7', '#FDEDEB', '#F8DED9', '#F2E4E1', '#AB4A43'
        elif variant == 'nav':
            selected = self._button_options['selected']
            base, hover, down = (WHITE, '#FAFCFF', '#EAF0F9') if selected else (background, '#E5EBF4', '#DCE5F1')
            border, text = ('#E3E9F2', BLUE) if selected else (background, '#63738A')
            shadow = '#DFE5EF' if selected else background
        elif variant == 'ghost':
            base, hover, down, border, text = background, LIGHT_BLUE, '#DCE6F4', background, TEXT
        else:
            base, hover, down, border, text = '#F8FAFD', '#EDF2FA', '#E1EAF7', '#E4EAF2', '#42536B'
        fill = down if pressed else hover if self._hover else base
        ring = '#ABC2E6' if self._focused and self._focus_visible else background
        offset = 1 if pressed else -0.5 if self._hover and variant != 'ghost' else 0
        return fill, border, text, shadow, ring, offset

    def _refresh(self, animate=True):
        palette = self._palette()
        target = tuple(_rgb(color) for color in palette[:5]) + (palette[5],)
        if target == self._target:
            return
        if self._animation is not None:
            self.after_cancel(self._animation)
            self._animation = None
        self._target = target
        start = self._current or target
        started = time.perf_counter()
        duration = 0.055 if self._mouse_down or self._key_down else 0.14
        if not animate or self._current is None:
            duration = 0

        def step():
            progress = min(1, (time.perf_counter() - started) / duration) if duration else 1
            eased = 1 - (1 - progress) ** 3
            colors = tuple(tuple(round(a + (b - a) * eased) for a, b in zip(first, last))
                           for first, last in zip(start[:5], target[:5]))
            self._current = colors + (start[5] + (target[5] - start[5]) * eased,)
            self._paint()
            self._animation = self.after(16, step) if progress < 1 else None

        step()

    def _paint(self):
        width, height = self.winfo_width(), self.winfo_height()
        if width < 8 or height < 8:
            return
        colors, offset = self._current[:5], self._current[5]
        icon_x = (width - self._content_width) / 2
        image = _button_surface(width, height, _rgb(self.cget('bg')), colors,
                                round(offset * 3), self._button_options['variant'],
                                self._button_options['icon'], round(icon_x * 3), self._icon_size)
        self._photo = ImageTk.PhotoImage(image, master=self)
        self.itemconfigure(self._surface, image=self._photo)
        self.coords(self._caption, width / 2 + self._icon_space / 2, height / 2 - 1 + offset)
        self.itemconfigure(self._caption, fill='#' + ''.join(f'{channel:02x}' for channel in colors[2]))

    def _set_hover(self, value):
        self._hover = value
        self._refresh()

    def _set_focus(self, value):
        self._focused = value
        self._focus_visible = value and not self._pointer_focus
        if not value:
            self._pointer_focus = False
            self._mouse_down, self._key_down = False, None
        self._refresh()

    def _press(self, event):
        if self._button_options['state'] != 'disabled':
            self._pointer_focus = True
            self._focus_visible = False
            self.focus_set()
            self._mouse_down = self._hover = True
            self._refresh()
        return 'break'

    def _release(self, event):
        activate = self._mouse_down and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
        self._mouse_down = False
        self._refresh()
        if activate:
            self.invoke()
        return 'break'

    def _key_press(self, event):
        if self._button_options['state'] != 'disabled' and self._key_down is None:
            self._pointer_focus = False
            self._focus_visible = True
            self._key_down = event.keysym
            self._refresh()
        return 'break'

    def _key_release(self, event):
        if event.keysym != self._key_down:
            return 'break'
        activate = self._key_down is not None
        self._key_down = None
        self._refresh()
        if activate:
            self.invoke()
        return 'break'

    def _cancel_press(self, event):
        if self._key_down or self._mouse_down:
            self._mouse_down, self._key_down = False, None
            self._refresh()
            return 'break'

    def _cleanup(self, event):
        if event.widget is self and self._animation is not None:
            self.after_cancel(self._animation)
            self._animation = None


@lru_cache(maxsize=128)
def _rgb(color):
    return tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))


@lru_cache(maxsize=160)
def _button_surface(width, height, background, colors, offset, variant, icon, icon_x, icon_size):
    """Vẽ ở độ phân giải gấp ba rồi thu nhỏ; cache chỉ chứa ảnh PIL, không giữ cửa sổ Tk."""
    scale = 3
    image = Image.new('RGB', (width * scale, height * scale), background)
    draw = ImageDraw.Draw(image)
    fill, border, text, shadow, ring = colors
    radius = min(11 if height >= 38 else 9, (height - 8) / 2) * scale
    bounds = (3 * scale, 3 * scale + offset, (width - 3) * scale, (height - 5) * scale + offset)
    if ring != background:
        draw.rounded_rectangle((scale, scale, (width - 1) * scale, (height - 2) * scale),
                               radius=radius + 2 * scale, outline=ring, width=scale)
    if shadow != background:
        draw.rounded_rectangle((3 * scale, 5 * scale, (width - 3) * scale, (height - 3) * scale),
                               radius=radius, fill=shadow)
    draw.rounded_rectangle(bounds, radius=radius, fill=fill, outline=border, width=scale)
    if icon:
        _draw_icon(draw, icon, icon_x, round((height / 2 - 1 - icon_size / 2) * scale) + offset,
                   icon_size * scale, text, scale)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def _draw_icon(draw, name, x, y, size, color, stroke):
    def point(a, b):
        return x + a * size, y + b * size

    def line(points):
        draw.line([point(a, b) for a, b in points], fill=color, width=stroke, joint='curve')

    if name == 'plus':
        line(((0.5, 0.16), (0.5, 0.84)))
        line(((0.16, 0.5), (0.84, 0.5)))
    elif name == 'check':
        line(((0.15, 0.5), (0.4, 0.76), (0.86, 0.23)))
    elif name == 'calendar':
        draw.rounded_rectangle((*point(0.13, 0.22), *point(0.88, 0.9)), radius=stroke * 1.5,
                               outline=color, width=stroke)
        line(((0.13, 0.43), (0.88, 0.43)))
        line(((0.33, 0.09), (0.33, 0.33)))
        line(((0.68, 0.09), (0.68, 0.33)))
    elif name == 'chart':
        for left, top in ((0.18, 0.55), (0.44, 0.3), (0.7, 0.12)):
            draw.rounded_rectangle((*point(left, top), *point(left + 0.13, 0.86)),
                                   radius=stroke / 2, fill=color)
    elif name == 'list':
        for row in (0.25, 0.5, 0.75):
            line(((0.36, row), (0.88, row)))
            draw.ellipse((*point(0.12, row - 0.04), *point(0.2, row + 0.04)), fill=color)
    elif name == 'trash':
        line(((0.15, 0.24), (0.85, 0.24)))
        line(((0.35, 0.22), (0.35, 0.12), (0.65, 0.12), (0.65, 0.22)))
        line(((0.25, 0.33), (0.3, 0.88), (0.7, 0.88), (0.75, 0.33)))
        line(((0.43, 0.39), (0.44, 0.73)))
        line(((0.58, 0.39), (0.57, 0.73)))


def make_icon_image(parent, name, size=32, color=BLUE, gap=0):
    """Dùng cùng nét vẽ với icon trên nút, có thể chừa khoảng cách trước chữ."""
    scale = 3
    image = Image.new('RGBA', ((size + gap) * scale, size * scale))
    _draw_icon(ImageDraw.Draw(image), name, 2 * scale, 2 * scale,
               (size - 4) * scale, color, max(3, round(size / 14 * scale)))
    return ImageTk.PhotoImage(image.resize((size + gap, size), Image.Resampling.LANCZOS), master=parent)


class RoundedPanel(tk.Canvas):
    """Khay điều hướng bo góc; các nút bên trong vẫn dùng pack bình thường."""

    def __init__(self, parent):
        super().__init__(parent, bg=parent.cget('bg'), bd=0, highlightthickness=0, takefocus=0)
        self.content = tk.Frame(self, bg='#EFF3F9')
        self._image = self.create_image(0, 0, anchor='nw')
        self._window = self.create_window(5, 3, window=self.content, anchor='nw')
        self.content.bind('<Configure>', self._resize)

    def _resize(self, event=None):
        width, height = self.content.winfo_reqwidth() + 10, self.content.winfo_reqheight() + 6
        self.configure(width=width, height=height)
        scale = 3
        image = Image.new('RGB', (width * scale, height * scale), self.cget('bg'))
        ImageDraw.Draw(image).rounded_rectangle((0, 0, width * scale - 1, height * scale - 1),
                                               radius=14 * scale, fill='#EFF3F9')
        self._photo = ImageTk.PhotoImage(image.resize((width, height), Image.Resampling.LANCZOS), master=self)
        self.itemconfigure(self._image, image=self._photo)


def make_button(parent, text, command, primary=False, *, variant=None, compact=False, icon=None):
    if icon is None:
        if text.startswith('+ '):
            icon = 'plus'
        elif text.startswith('Xóa'):
            icon = 'trash'
        elif text.startswith('Lưu ') or text in ('Xong', 'Đánh dấu xong'):
            icon = 'check'
        elif text == 'Lịch':
            icon = 'calendar'
    return RoundedButton(parent, text, command,
                         variant=variant or ('primary' if primary else 'secondary'),
                         compact=compact, icon=icon)


class AutoScrollbar(ttk.Scrollbar):
    """Thanh cuộn dùng grid, chỉ hiện khi nội dung cần cuộn."""

    def set(self, first, last):
        visible = float(first) > 0.0001 or float(last) < 0.9999
        if visible and not self.winfo_manager():
            self.grid()
        elif not visible and self.winfo_manager():
            self.grid_remove()
        super().set(first, last)


def tao_bang(parent, columns, height=6, expand=True, *, style='Task.Treeview', auto_scroll=False):
    """Bảng có thanh cuộn; mỗi cột gồm tên trong code, nhãn và chiều rộng."""
    frame = tk.Frame(parent, bg=WHITE)
    frame.pack(fill='both' if expand else 'x', expand=expand)
    tree = ttk.Treeview(frame,
        columns=[column[0] for column in columns],
        show='headings',
        selectmode='browse',
        height=height,
        style=style)
    for index, (key, label, width) in enumerate(columns):
        tree.heading(key, text=label, anchor='w')
        tree.column(key, width=width, minwidth=70, stretch=index == 0)
    scrollbar = AutoScrollbar if auto_scroll else ttk.Scrollbar
    prefix = 'Calendar' if auto_scroll else 'Slim'
    vertical = scrollbar(frame, command=tree.yview, style=f'{prefix}.Vertical.TScrollbar')
    horizontal = scrollbar(frame,
        orient='horizontal',
        command=tree.xview,
        style=f'{prefix}.Horizontal.TScrollbar')
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
    style = ttk.Style(window)
    style.theme_use('clam')
    configure_calendar_styles(window, style)
    # Notebook chỉ giữ các trang; bộ chọn riêng đảm nhiệm hiển thị và focus.
    style.configure('Stats.TNotebook', background=BG, borderwidth=0,
                    padding=0, tabmargins=0)
    style.configure('Stats.TNotebook.Tab', padding=0)
    style.layout('Stats.TNotebook', [])
    style.layout('Stats.TNotebook.Tab', [])
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


def configure_calendar_styles(window, style):
    """Style riêng cho vùng điều khiển/bảng lịch; không đổi các trang khác."""
    style.configure('Calendar.TCombobox', font=('Segoe UI', 9), padding=(9, 5),
                    background='#F8FAFD', fieldbackground='#F8FAFD', foreground=TEXT,
                    arrowcolor=MUTED, bordercolor=BORDER, lightcolor=BORDER,
                    darkcolor=BORDER, arrowsize=13, borderwidth=1, relief='flat')
    style.map('Calendar.TCombobox',
              fieldbackground=[('focus', WHITE), ('readonly', '#F8FAFD')],
              background=[('active', LIGHT_BLUE), ('readonly', '#F8FAFD')],
              foreground=[('readonly', TEXT)],
              selectbackground=[('readonly', '#F8FAFD')], selectforeground=[('readonly', TEXT)],
              bordercolor=[('focus', '#A9C0E3')],
              lightcolor=[('focus', '#A9C0E3')], darkcolor=[('focus', '#A9C0E3')])
    style.configure('Calendar.TCheckbutton', background=WHITE, foreground=MUTED,
                    font=('Segoe UI', 9), padding=(2, 4), indicatorbackground=WHITE,
                    indicatorcolor=WHITE, indicatormargin=(0, 0, 7, 0), focuscolor=BLUE)
    style.map('Calendar.TCheckbutton', background=[('active', WHITE)],
              foreground=[('selected', BLUE), ('active', TEXT)],
              indicatorbackground=[('selected', BLUE), ('active', '#F8FAFD')],
              indicatorcolor=[('selected', WHITE)])
    style.configure('Calendar.Treeview', background=WHITE, fieldbackground=WHITE,
                    foreground=TEXT, rowheight=32, font=('Segoe UI', 10),
                    borderwidth=0, relief='flat', lightcolor=WHITE, darkcolor=WHITE)
    style.layout('Calendar.Treeview', [('Treeview.treearea', {'sticky': 'nswe'})])
    style.configure('Calendar.Treeview.Heading', background='#F3F6FB', foreground='#65758B',
                    font=('Segoe UI Semibold', 9), padding=(10, 7), relief='flat', borderwidth=0)
    style.map('Calendar.Treeview.Heading', background=[('active', '#EAF0F8')], relief=[('active', 'flat')])
    style.map('Calendar.Treeview', background=[('selected', '#E8F0FC')], foreground=[('selected', '#294F85')])
    if not hasattr(window, '_calendar_scroll_images'):
        window._calendar_scroll_images = []
    for direction in ('Vertical', 'Horizontal'):
        element = f'Calendar.{direction}.Scrollbar.thumb'
        trough = f'Calendar.{direction}.Scrollbar.trough'
        if trough not in style.element_names():
            track = tk.PhotoImage(master=window, width=8, height=8)
            track.put('#F4F7FB', to=(0, 0, 8, 8))
            window._calendar_scroll_images.append(track)
            style.element_create(trough, 'image', track, sticky='nswe')
        if element not in style.element_names():
            width, height = (8, 24) if direction == 'Vertical' else (24, 8)
            images = []
            for color in ('#D2DDEA', '#B7C9E0', '#94AED0'):
                image = Image.new('RGBA', (width * 3, height * 3))
                ImageDraw.Draw(image).rounded_rectangle((2, 2, width * 3 - 3, height * 3 - 3),
                                                       radius=9, fill=color)
                photo = ImageTk.PhotoImage(image.resize((width, height), Image.Resampling.LANCZOS), master=window)
                images.append(photo)
            window._calendar_scroll_images.extend(images)
            style.element_create(element, 'image', images[0], ('pressed', images[2]), ('active', images[1]),
                                 border=(3, 3, 3, 3), sticky='nswe')
        name = f'Calendar.{direction}.TScrollbar'
        style.layout(name, [(trough, {
            'sticky': 'nswe', 'children': [(element, {'expand': True, 'sticky': 'nswe'})]})])
        style.configure(name, troughcolor=WHITE, background=WHITE, borderwidth=0,
                        lightcolor=WHITE, darkcolor=WHITE, arrowsize=8, gripcount=0)
