"""Ô nhập ngày có lịch chọn, dùng chung cho các biểu mẫu."""

import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

from ui import widgets
from ui.widgets import MUTED, TEXT, WHITE


class DateField(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=WHITE)
        self.entry = ttk.Entry(self, width=14, style='Form.TEntry')
        self.entry.pack(side='left', fill='x', expand=True)
        self.button = widgets.make_button(self, 'Lịch', self.open_calendar)
        self.button.pack(side='left', padx=(4, 0))
        self.entry.bind('<Alt-Down>', self.open_calendar)

    def open_calendar(self, event=None):
        owner = self.winfo_toplevel()
        previous = getattr(owner, '_date_picker', None)
        if previous is not None and previous.winfo_exists():
            if previous.field is self:
                previous.lift()
                return 'break'
            previous.close()
        owner._date_picker = CalendarPopup(self)
        return 'break'


class CalendarPopup(tk.Toplevel):
    def __init__(self, field):
        self.field = field
        owner = field.winfo_toplevel()
        super().__init__(owner)
        self.withdraw()
        self.title('Chọn ngày')
        self.configure(bg=WHITE)
        self.resizable(False, False)
        self.transient(owner)
        self.previous_grab = self.grab_current()
        try:
            self.selected = datetime.strptime(field.entry.get().strip(), '%d/%m/%Y').date()
        except ValueError:
            self.selected = None
        initial = self.selected or date.today()
        self.month = initial.replace(day=1)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', self.close)

        header = tk.Frame(self, bg=WHITE)
        header.pack(fill='x', padx=10, pady=(8, 4))
        self.previous_button = widgets.make_button(header, '‹', lambda: self.change_month(-1), compact=True)
        self.previous_button.pack(side='left')
        self.month_text = tk.StringVar(self)
        self.month_label = tk.Label(header, textvariable=self.month_text, bg=WHITE,
                                   fg=TEXT, font=('Segoe UI', 10, 'bold'))
        self.month_label.pack(side='left', fill='x', expand=True)
        self.next_button = widgets.make_button(header, '›', lambda: self.change_month(1), compact=True)
        self.next_button.pack(side='right')
        self.days = tk.Frame(self, bg=WHITE)
        self.days.pack(padx=10, pady=4)
        footer = tk.Frame(self, bg=WHITE)
        footer.pack(fill='x', padx=10, pady=(4, 8))
        today_button = widgets.make_button(footer, 'Hôm nay', lambda: self.choose(date.today()), compact=True)
        today_button.pack(side='left')
        close_button = widgets.make_button(footer, 'Đóng', self.close, compact=True)
        close_button.pack(side='right')
        self.draw_month()

        self.update_idletasks()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        x = max(0, min(field.winfo_rootx(), self.winfo_screenwidth() - width))
        y = field.winfo_rooty() + field.winfo_height() + 4
        if y + height > self.winfo_screenheight() - 60:
            y = field.winfo_rooty() - height - 4
        y = max(0, min(y, self.winfo_screenheight() - height - 60))
        self.geometry(f'+{x}+{y}')
        self.deiconify()
        self.wait_visibility()
        self.grab_set()
        self.focus_day.focus_set()

    def draw_month(self):
        for child in self.days.winfo_children():
            child.destroy()
        self.month_text.set(f'Tháng {self.month.month} / {self.month.year}')
        self.previous_button.configure(state='disabled' if self.month == date.min else 'normal')
        self.next_button.configure(state='disabled' if self.month == date(9999, 12, 1) else 'normal')
        for column, name in enumerate(('T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN')):
            tk.Label(self.days, text=name, bg=WHITE, fg=MUTED,
                     font=('Segoe UI', 9), width=4).grid(row=0, column=column, pady=(0, 5))
        first_weekday, day_count = calendar.monthrange(self.month.year, self.month.month)
        today = date.today()
        self.day_buttons = {}
        for number in range(1, day_count + 1):
            day = self.month.replace(day=number)
            selected = day == self.selected
            variant = 'primary' if selected else 'secondary' if day == today else 'ghost'
            button = widgets.make_button(self.days, str(number), lambda chosen=day: self.choose(chosen),
                                         variant=variant, compact=True)
            button.configure(width=38, height=32, font=('Segoe UI', 10))
            row, column = divmod(first_weekday + number - 1, 7)
            button.grid(row=row + 1, column=column, padx=1, pady=1)
            self.day_buttons[number] = button
        for row in range(1, 7):
            self.days.rowconfigure(row, minsize=34)
        focus_date = self.selected or today
        focus_number = focus_date.day if (focus_date.year, focus_date.month) == (
            self.month.year, self.month.month) else 1
        self.focus_day = self.day_buttons[focus_number]

    def change_month(self, offset):
        index = (self.month.year - 1) * 12 + self.month.month - 1 + offset
        if 0 <= index < 9999 * 12:
            year, month = divmod(index, 12)
            self.month = date(year + 1, month + 1, 1)
            self.draw_month()
            self.focus_day.focus_set()

    def choose(self, chosen):
        self.field.entry.delete(0, 'end')
        self.field.entry.insert(0, f'{chosen.day:02d}/{chosen.month:02d}/{chosen.year:04d}')
        return self.close()

    def close(self, event=None):
        self.destroy()
        if self.previous_grab is not None and self.previous_grab.winfo_exists():
            self.previous_grab.grab_set()
        if self.field.winfo_exists():
            self.field.entry.focus_set()
        return 'break'
