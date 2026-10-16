"""Chuẩn bị dữ liệu lịch; không tạo widget và không thay đổi database."""

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


def visible_tasks(tasks, collapsed):
    """Ẩn các con của nhánh đã thu gọn, không làm mất dữ liệu của nhánh."""
    hidden = set()
    result = []
    for task in tasks:
        if task['parent_id'] in hidden:
            hidden.add(task['id'])
            continue
        result.append(task)
        if task['id'] in collapsed:
            hidden.add(task['id'])
    return result


def date_range(tasks, selected_day, today=None):
    """Luôn chứa hôm nay, ngày đang xem và toàn bộ khoảng đã lên lịch."""
    today = today or date.today()
    dates = [today, selected_day]
    for task in tasks:
        if task['scheduled']:
            dates.extend((task['calendar_start'], task['calendar_end']))
    start = min(dates)
    end = max(dates)
    # Có lề để thanh đầu/cuối không dính sát mép lịch.
    start -= timedelta(days=min(3, start.toordinal() - 1))
    end += timedelta(days=min(7, date.max.toordinal() - end.toordinal()))
    return start, end


def tasks_for_period(tasks, selected_day, mode, include_done=False):
    """Chỉ chọn task lá; xét giao khoảng ngày, không chỉ ngày bắt đầu."""
    start = selected_day
    end = selected_day
    if mode == 'Tuần':
        start -= timedelta(days=start.weekday())
        end = start + timedelta(days=6)
    result = []
    for task in tasks:
        if task['has_children']:
            continue
        if not include_done and task['is_done'] == 1:
            continue
        if mode == 'Chưa xếp lịch':
            matches = not task['scheduled']
        else:
            matches = (task['scheduled'] and task['calendar_start'] <= end
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
