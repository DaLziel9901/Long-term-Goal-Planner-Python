"""Vẽ trục thời gian bằng Tkinter Canvas, không truy vấn database."""

from datetime import date, timedelta

from ui import calendar_data, state
from ui.widgets import BLUE, BORDER, LIGHT_BLUE, MUTED, SOFT, TEXT, WHITE

DAY_WIDTH = 42
ROW_HEIGHT = 42
HEADER_HEIGHT = 68
NAME_WIDTH = 260
GREEN = '#39806A'


def day_x(day):
    return (day - state.calendar_start).days * DAY_WIDTH


def scroll_to_day(day):
    canvas = state.calendar_canvas
    canvas.update_idletasks()
    width = max(1, state.calendar_width)
    canvas.xview_moveto(max(0, day_x(day) - canvas.winfo_width() / 3) / width)


def draw_grid():
    """Chỉ vẽ cột ngày đang nhìn thấy để lịch nhiều năm không có quá nhiều ô."""
    canvas = state.calendar_canvas
    header = state.calendar_header
    canvas.delete('grid')
    canvas.delete('today')
    header.delete('all')
    first = max(0, int(canvas.canvasx(0) // DAY_WIDTH))
    last = min(state.calendar_days, first + canvas.winfo_width() // DAY_WIDTH + 3)
    height = max(ROW_HEIGHT, len(state.calendar_rows) * ROW_HEIGHT)
    selected = state.selected_day
    mode = state.calendar_mode.get()
    selection_start = selected - timedelta(days=selected.weekday()) if mode == 'Tuần' else selected
    selection_end = selection_start + timedelta(days=6) if mode == 'Tuần' else selected
    for offset in range(first, last):
        day = state.calendar_start + timedelta(days=offset)
        x = offset * DAY_WIDTH
        color = SOFT if day.weekday() >= 5 else WHITE
        selected_cell = mode != 'Chưa xếp lịch' and selection_start <= day <= selection_end
        header.create_rectangle(x, 0, x + DAY_WIDTH, HEADER_HEIGHT,
                                fill=LIGHT_BLUE if selected_cell else color, outline=BORDER)
        header.create_text(x + DAY_WIDTH / 2, 12, text=day.strftime('%m/%Y'),
                           fill=MUTED, font=('Segoe UI', 8))
        header.create_text(x + DAY_WIDTH / 2, 32, text=str(day.day),
                           fill=BLUE if day == date.today() else TEXT,
                           font=('Segoe UI', 10, 'bold'))
        percent = calendar_data.day_completion(state.calendar_tasks, day)
        if percent is not None:
            header.create_rectangle(x + 3, 60, x + 3 + (DAY_WIDTH - 6) * percent / 100, 65,
                                    fill=GREEN, outline='')
        header.create_text(x + DAY_WIDTH / 2, 49,
                           text='—' if percent is None else f'{percent:.0f}%',
                           fill=GREEN if percent == 100 else MUTED, font=('Segoe UI', 8))
        canvas.create_rectangle(x, 0, x + DAY_WIDTH, height,
                                fill=LIGHT_BLUE if day == date.today() else color,
                                outline='', tags='grid')
        canvas.create_line(x, 0, x, height, fill=BORDER, tags='grid')
        if day == date.today():
            canvas.create_line(x + DAY_WIDTH / 2, 0, x + DAY_WIDTH / 2, height,
                               fill=BLUE, width=2, tags='today')
    canvas.tag_lower('grid')
    canvas.tag_raise('today')


def draw(on_select, on_toggle, on_edit):
    """Một dòng cho mỗi task; nền chỉ thời gian, dải bên trong chỉ tiến độ."""
    canvas = state.calendar_canvas
    names = state.calendar_names
    canvas.delete('all')
    names.delete('all')
    state.calendar_rows = calendar_data.visible_tasks(state.calendar_tasks, state.calendar_collapsed)
    state.calendar_start, state.calendar_end = calendar_data.date_range(
        state.calendar_tasks, state.selected_day)
    state.calendar_days = (state.calendar_end - state.calendar_start).days + 1
    state.calendar_width = state.calendar_days * DAY_WIDTH
    height = max(ROW_HEIGHT, len(state.calendar_rows) * ROW_HEIGHT)
    canvas.configure(scrollregion=(0, 0, state.calendar_width, height))
    names.configure(scrollregion=(0, 0, NAME_WIDTH, height))
    state.calendar_header.configure(scrollregion=(0, 0, state.calendar_width, HEADER_HEIGHT))
    # Đồng bộ vị trí sau khi tổng số dòng thay đổi do xóa hoặc thu gọn.
    names.yview_moveto(canvas.yview()[0])
    state.calendar_header.xview_moveto(canvas.xview()[0])
    for row, task in enumerate(state.calendar_rows):
        ident = task['id']
        y = row * ROW_HEIGHT
        tag = f'task_{ident}'
        selected = ident == state.calendar_selected_task
        names.create_rectangle(0, y, NAME_WIDTH, y + ROW_HEIGHT,
                               fill=LIGHT_BLUE if selected else WHITE, outline=BORDER, tags=tag)
        indent = 8 + min(task['level'], 8) * 16
        if task['has_children']:
            triangle = '▶' if ident in state.calendar_collapsed else '▼'
            item = names.create_text(indent + 6, y + 20, text=triangle, fill=BLUE)
            names.tag_bind(item, '<Button-1>', lambda event, task_id=ident: on_toggle(task_id))
        title = task['title']
        limit = max(8, (NAME_WIDTH - indent - 72) // 8)
        if len(title) > limit:
            title = title[:limit - 1] + '…'
        names.create_text(indent + 18, y + 20, text=title, anchor='w', fill=TEXT,
                          font=('Segoe UI', 9), tags=tag)
        names.create_text(NAME_WIDTH - 8, y + 20, text=f"{task['progress']:.0f}%",
                          anchor='e', fill=GREEN if task['progress'] == 100 else BLUE,
                          font=('Segoe UI', 9, 'bold'), tags=tag)
        names.tag_bind(tag, '<Button-1>', lambda event, task_id=ident: on_select(task_id))
        names.tag_bind(tag, '<Double-1>', lambda event, task_id=ident: on_edit(task_id))
        canvas.create_line(0, y + ROW_HEIGHT, state.calendar_width, y + ROW_HEIGHT,
                           fill=BORDER)
        if not task['scheduled']:
            canvas.create_text(12, y + 20, text='Chưa đủ ngày bắt đầu / kết thúc',
                               anchor='w', fill=MUTED, font=('Segoe UI', 9), tags=tag)
        else:
            x1 = day_x(task['calendar_start']) + 3
            x2 = day_x(task['calendar_end']) + DAY_WIDTH - 3
            color = GREEN if task['progress'] == 100 else BLUE
            canvas.create_rectangle(x1, y + 8, x2, y + 33,
                                    fill='#EAF4EF' if task['progress'] == 100 else LIGHT_BLUE,
                                    outline=color, width=2 if selected else 1, tags=tag)
            # Dải tiến độ không mang ý nghĩa đã làm xong những ngày bên trái.
            if task['progress'] > 0:
                canvas.create_rectangle(x1, y + 27, x1 + (x2 - x1) * task['progress'] / 100,
                                        y + 33, fill=color, outline='', tags=tag)
            label = f"{'✓ ' if task['progress'] == 100 else ''}{task['progress']:.0f}%"
            canvas.create_text(x1 + 5, y + 17, text=label, anchor='w', fill=color,
                               font=('Segoe UI', 8), tags=tag)
        canvas.tag_bind(tag, '<Button-1>', lambda event, task_id=ident: on_select(task_id))
        canvas.tag_bind(tag, '<Double-1>', lambda event, task_id=ident: on_edit(task_id))
    if not state.calendar_rows:
        names.create_text(12, 20, text='Chưa có mục tiêu', anchor='w', fill=MUTED)
    draw_grid()
