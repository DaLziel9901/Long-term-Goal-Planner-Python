"""Chuẩn bị dữ liệu lịch; không tạo widget và không thay đổi database."""

from calendar import monthrange
from datetime import date, timedelta

from ui import data


def read_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def load_calendar_tasks():
    """Lấy cả mục tiêu gốc và mọi cấp con theo thứ tự cây."""
    roots = data.load_projects()
    descendants = data.danh_sach_cong_viec()
    children = {}
    for task in descendants:
        children.setdefault(task['parent_id'], []).append(task)
    result = []

    def collect(task):
        start = read_date(task['start_date'])
        end = read_date(task['end_date'])
        scheduled = start is not None and end is not None and start <= end
        result.append(dict(
            task, calendar_start=start, calendar_end=end,
            scheduled=scheduled, has_children=bool(children.get(task['id'])),
        ))
        for child in children.get(task['id'], []):
            collect(child)

    for root in roots:
        collect(root)
    return result


def tasks_for_period(tasks, selected_day, mode, include_done=False):
    """Task có ngày lấy task lá; task thiếu ngày nằm trong nhóm riêng."""
    start = selected_day
    end = selected_day
    if mode == 'Tuần':
        start -= timedelta(days=start.weekday())
        end = start + timedelta(days=6)
    result = []
    for task in tasks:
        if not include_done and task['progress'] == 100:
            continue
        if not task['scheduled']:
            matches = mode in ('Chưa xếp lịch', 'Tuần')
        else:
            matches = (mode != 'Chưa xếp lịch' and not task['has_children'] and task['calendar_start'] <= end
                       and task['calendar_end'] >= start)
        if matches:
            result.append(task)
    return result


def day_completion(tasks, day):
    """Tiến độ kế hoạch của ngày: số task lá đã xong / số task lá phủ ngày."""
    leaves = [task for task in tasks if not task['has_children'] and task['scheduled']
              and task['calendar_start'] <= day <= task['calendar_end']]
    if not leaves:
        return None
    return sum(task['is_done'] == 1 for task in leaves) * 100 / len(leaves)


def shift_month(day, offset):
    """Chuyển tháng, giữ ngày nếu có thể (31/01 → 28/02 hoặc 29/02)."""
    index = (day.year - 1) * 12 + day.month - 1 + offset
    index = max(0, min(9999 * 12 - 1, index))
    year, month = index // 12 + 1, index % 12 + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def heatmap_range(tasks, selected_day, today=None):
    """Ít nhất sáu tháng; chỉ task có đủ ngày mới mở rộng khoảng lịch."""
    today = today or date.today()
    days = [shift_month(today, -2), shift_month(today, 3), selected_day]
    for task in tasks:
        if task['scheduled']:
            days.extend((task['calendar_start'], task['calendar_end']))
    first = min(days).replace(day=1)
    last = max(days)
    last = last.replace(day=monthrange(last.year, last.month)[1])
    return first, last


def tasks_in_scope(tasks, task_id):
    """Một mục tiêu gồm chính nó và toàn bộ con cháu, không đếm cha hai lần."""
    if task_id is None:
        return tasks
    selected = {task_id}
    result = []
    for task in tasks:
        if task['id'] == task_id or task['parent_id'] in selected:
            selected.add(task['id'])
            result.append(task)
    return result
