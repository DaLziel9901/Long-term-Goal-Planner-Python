"""Heatmap bảy hàng theo thứ, mỗi tháng là một khối cách nhau khoảng trắng."""

from calendar import monthrange
from datetime import date, timedelta

from ui import calendar_data, state
from ui.widgets import BLUE, BORDER, MUTED, TEXT, WHITE

CELL_SIZE = 26
CELL_GAP = 4
CELL_STEP = CELL_SIZE + CELL_GAP
MONTH_GAP = 22
PADDING = 4
HEADER_HEIGHT = 26
NAME_WIDTH = 50
GRID_HEIGHT = 7 * CELL_STEP + PADDING
DEADLINE_COLOR = '#B5473C'


def month_layout(first, last):
    """Tính vị trí từng tháng; tuần giao tháng được tách, không lặp ngày."""
    months = []
    month = first.replace(day=1)
    x = PADDING
    while month <= last:
        count = monthrange(month.year, month.month)[1]
        columns = (month.weekday() + count + 6) // 7
        width = columns * CELL_STEP - CELL_GAP
        months.append(dict(start=month, end=month.replace(day=count),
                           x=x, width=width, columns=columns))
        x += width + MONTH_GAP
        next_month = calendar_data.shift_month(month, 1)
        if next_month <= month:
            break
        month = next_month
    return months


def cell_position(day):
    block = state.calendar_month_lookup[(day.year, day.month)]
    column = (block['start'].weekday() + day.day - 1) // 7
    return block['x'] + column * CELL_STEP, PADDING + day.weekday() * CELL_STEP


def day_at(x, y):
    """Bỏ qua khoảng cách tháng, khe giữa ô và các ô trống đầu/cuối tháng."""
    y -= PADDING
    if y < 0:
        return None
    row, dy = divmod(int(y), CELL_STEP)
    if row >= 7 or dy >= CELL_SIZE:
        return None
    for block in state.calendar_months:
        if x < block['x']:
            return None
        if x >= block['x'] + block['width']:
            continue
        column, dx = divmod(int(x - block['x']), CELL_STEP)
        number = column * 7 + row - block['start'].weekday() + 1
        if dx >= CELL_SIZE or not 1 <= number <= block['end'].day:
            return None
        return block['start'].replace(day=number)
    return None


def scroll_to_day(day):
    canvas = state.calendar_canvas
    canvas.update_idletasks()
    x, _ = cell_position(day)
    canvas.xview_moveto(max(0, x - canvas.winfo_width() / 3) / max(1, state.calendar_width))


def heat_color(percent):
    if percent is None:
        return '#F1F3F6'
    if percent == 0:
        return '#E2E8EE'
    if percent < 25:
        return '#C6EACB'
    if percent < 50:
        return '#8ED49B'
    if percent < 75:
        return '#56B870'
    if percent < 100:
        return '#2D914B'
    return '#166534'


def draw_months(months):
    header = state.calendar_header
    header.delete('all')
    left = state.calendar_canvas.canvasx(0)
    right = left + state.calendar_canvas.winfo_width()
    for block in months:
        visible_left = max(block['x'], left)
        visible_right = min(block['x'] + block['width'], right)
        if visible_right - visible_left >= 85:
            month = block['start']
            header.create_text(visible_left + 3, HEADER_HEIGHT / 2, anchor='w',
                               text=f'Tháng {month.month}/{month.year}',
                               fill=TEXT, font=('Segoe UI', 9, 'bold'), tags='month_title')


def draw_plan(months):
    """Dải kế hoạch ngắt ở ranh giới tháng, chỉ vẽ task có đủ ngày."""
    task = next((task for task in state.calendar_tasks
                 if task['id'] == state.calendar_selected_task), None)
    if task is None or not task['scheduled']:
        return
    canvas = state.calendar_canvas
    for block in months:
        start = max(task['calendar_start'], block['start'])
        end = min(task['calendar_end'], block['end'])
        if start > end:
            continue
        first = block['start'].weekday() + start.day - 1
        last = block['start'].weekday() + end.day - 1
        for column in range(first // 7, last // 7 + 1):
            first_row = max(0, first - column * 7)
            last_row = min(6, last - column * 7)
            x = block['x'] + column * CELL_STEP
            canvas.create_rectangle(
                x + CELL_SIZE - 8, PADDING + first_row * CELL_STEP + 2,
                x + CELL_SIZE - 3, PADDING + last_row * CELL_STEP + CELL_SIZE - 2,
                fill=BLUE, outline='', tags='plan',
            )
    x, y = cell_position(task['calendar_end'])
    canvas.create_polygon(x + 3, y + 17, x + 12, y + 17, x + 3, y + 24,
                          fill=DEADLINE_COLOR, outline='', tags='deadline')


def draw_grid():
    """Chỉ vẽ tháng và ô đang nhìn thấy; nền trắng giữa các tháng được giữ trống."""
    canvas = state.calendar_canvas
    canvas.delete('all')
    left = canvas.canvasx(0)
    right = left + canvas.winfo_width()
    months = [block for block in state.calendar_months
              if block['x'] + block['width'] > left and block['x'] < right]
    draw_months(months)
    for block in months:
        for number in range(1, block['end'].day + 1):
            day = block['start'].replace(day=number)
            x, y = cell_position(day)
            if x + CELL_SIZE < left or x > right:
                continue
            percent = calendar_data.day_completion(state.calendar_scope_tasks, day)
            tag = f'day_{day.isoformat()}'
            canvas.create_rectangle(x, y, x + CELL_SIZE, y + CELL_SIZE,
                                    fill=heat_color(percent), outline=BORDER, tags=(tag, 'cell'))
            canvas.create_text(x + 10, y + 10, text=str(day.day),
                               fill=WHITE if percent is not None and percent >= 75 else TEXT,
                               font=('Segoe UI', 9), tags=tag)
            if day == date.today():
                canvas.create_oval(x + 4, y + 19, x + 8, y + 23,
                                   fill=BLUE, outline='', tags='today')
            if day == state.selected_day:
                canvas.create_rectangle(x - 1, y - 1, x + CELL_SIZE + 1, y + CELL_SIZE + 1,
                                        outline=BLUE, width=2, tags='selected_day')
    draw_plan(months)


def draw_heatmap():
    state.calendar_start, state.calendar_end = calendar_data.heatmap_range(
        state.calendar_tasks, state.selected_day)
    state.calendar_months = month_layout(state.calendar_start, state.calendar_end)
    state.calendar_month_lookup = {(block['start'].year, block['start'].month): block
                                   for block in state.calendar_months}
    state.calendar_days = (state.calendar_end - state.calendar_start).days + 1
    state.calendar_weeks = sum(block['columns'] for block in state.calendar_months)
    last = state.calendar_months[-1]
    state.calendar_width = last['x'] + last['width'] + PADDING
    state.calendar_canvas.configure(scrollregion=(0, 0, state.calendar_width, GRID_HEIGHT))
    state.calendar_header.configure(scrollregion=(0, 0, state.calendar_width, HEADER_HEIGHT))
    state.calendar_names.delete('all')
    for row, name in enumerate(('T.Hai', 'T.Ba', 'T.Tư', 'T.Năm', 'T.Sáu', 'T.Bảy', 'C.Nhật')):
        state.calendar_names.create_text(NAME_WIDTH - 6, PADDING + row * CELL_STEP + CELL_SIZE / 2,
                                         text=name, anchor='e', fill=MUTED, font=('Segoe UI', 9))
    state.calendar_header.xview_moveto(state.calendar_canvas.xview()[0])
    draw_grid()
