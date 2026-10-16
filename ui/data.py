"""Kiểm tra dữ liệu nhập và gọi các hàm database; không tạo widget."""


import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta

from database import (
    calc_progress,
    create_database,
    delete_task,
    get_children,
    get_connection,
    get_task_by_id,
    insert_task,
    update_task,
)


TRANG_THAI_CONG_VIEC = ("Chưa làm", "Hoàn thành")


def connect_database():
    return get_connection()


def init_database():
    create_database()
    # Chỉ kiểm tra cấu trúc, không tự thay đổi bảng đang có.
    required = {'id',
        'parent_id',
        'root_id',
        'level',
        'title',
        'description',
        'start_date',
        'end_date',
        'is_done',
        'is_random',
        'order_index'}
    with closing(get_connection()) as connection:
        columns = {row['name'] for row in connection.execute('PRAGMA table_info(Task)')}
    missing = required - columns
    if missing:
        raise sqlite3.DatabaseError('Bảng Task thiếu cột: ' + ', '.join(sorted(missing)) + '. Cần cập nhật cấu trúc database trước khi sử dụng.')
    get_children(None)


def parse_input_date(value, field_name):
    value = (value or '').strip()
    if not value:
        return None
    if not re.fullmatch('[0-9]{2}/[0-9]{2}/[0-9]{4}', value):
        raise ValueError(f'{field_name} cần có định dạng DD/MM/YYYY.')
    try:
        return datetime.strptime(value, '%d/%m/%Y').date().isoformat()
    except ValueError:
        raise ValueError(f'{field_name} không hợp lệ.') from None


def du_lieu_hien_thi(task):
    """Đổi tên trường cho widget cũ; không đổi cấu trúc bảng Task."""
    progress = calc_progress(task['id'])
    status = 'Hoàn thành' if progress == 100 else 'Đang làm' if progress > 0 else 'Chưa làm'
    root = get_task_by_id(task['root_id'])
    return dict(task,
        name=task['title'],
        project_id=task['parent_id'],
        project_name=root['title'] if root else task['title'],
        planned_date=task['start_date'],
        due_date=task['end_date'],
        status=status,
        progress=progress)


def kiem_tra_cong_viec(name, description, planned_date, due_date, status):
    name = (name or '').strip()
    if not name:
        raise ValueError('Vui lòng nhập tên mục tiêu / công việc.')
    planned = parse_input_date(planned_date, 'Ngày bắt đầu')
    due = parse_input_date(due_date, 'Hạn hoàn thành')
    if planned and due and (due < planned):
        raise ValueError('Hạn hoàn thành không được trước ngày bắt đầu.')
    if status not in TRANG_THAI_CONG_VIEC:
        raise ValueError('Vui lòng chọn trạng thái hợp lệ.')
    return (name, (description or '').strip(), planned, due, status)


def add_project(name, description='', start_date='', end_date=''):
    name, description, start, end, _ = kiem_tra_cong_viec(name, description, start_date, end_date, 'Chưa làm')
    return insert_task(None, name, description, start, end)


def load_projects():
    return [du_lieu_hien_thi(task) for task in get_children(None)]


def get_project(exam):
    if isinstance(exam, int):
        task = get_task_by_id(exam)
        return du_lieu_hien_thi(task) if task else None
    return next((task for task in load_projects() if task['name'] == exam), None)


def xoa_du_an(project_id):
    if delete_task(project_id) == 0:
        raise ValueError('Mục tiêu không còn tồn tại.')


def them_cong_viec(project_id, name, description='', planned_date='', due_date='', status='Chưa làm'):
    name, description, start, end, status = kiem_tra_cong_viec(name,
        description,
        planned_date,
        due_date,
        status)
    if project_id is None:
        raise ValueError('Hãy chọn mục tiêu cha trước khi thêm công việc.')
    return insert_task(project_id, name, description, start, end, is_done=int(status == 'Hoàn thành'))


def sua_cong_viec(task_id, name, description='', planned_date='', due_date='', status='Chưa làm'):
    task = get_task_by_id(task_id)
    if task is None:
        raise ValueError('Công việc không còn tồn tại.')
    children = get_children(task_id)
    # Task có con bỏ qua trạng thái nhập; tiến độ do các con quyết định.
    name, description, start, end, status = kiem_tra_cong_viec(name,
        description,
        planned_date,
        due_date,
        'Chưa làm' if children else status)
    # update_task hiểu None là giữ nguyên, chưa hỗ trợ đặt lại ngày thành NULL.
    if (task['start_date'] and start is None) or (task['end_date'] and end is None):
        raise ValueError('Chưa hỗ trợ xóa ngày đã lưu. Hãy giữ ngày cũ hoặc nhập ngày mới.')
    if not update_task(task_id,
        title=name,
        description=description,
        start_date=start,
        end_date=end,
        is_done=None if children else int(status == 'Hoàn thành')):
        raise ValueError('Công việc không còn tồn tại.')


def xoa_cong_viec(task_id):
    if delete_task(task_id) == 0:
        raise ValueError('Công việc không còn tồn tại.')


def doi_trang_thai(task_id, status):
    if status not in TRANG_THAI_CONG_VIEC:
        raise ValueError('Vui lòng chọn trạng thái hợp lệ.')
    if get_children(task_id):
        raise ValueError('Task có con được tính tiến độ tự động. Hãy cập nhật các task lá.')
    if not update_task(task_id, is_done=int(status == 'Hoàn thành')):
        raise ValueError('Công việc không còn tồn tại.')


def lay_cong_viec(task_id):
    return get_project(task_id)


def danh_sach_cong_viec(project_id=None):
    """Trong chi tiết chỉ lấy con trực tiếp; toàn ứng dụng lấy mọi cấp con."""
    if project_id is not None:
        return [du_lieu_hien_thi(task) for task in get_children(project_id)]
    result = []

    def collect(parent_id):
        for task in get_children(parent_id):
            result.append(du_lieu_hien_thi(task))
            collect(task['id'])
    for root in get_children(None):
        collect(root['id'])
    return result


def cong_viec_trong_tuan(ngay_dau_tuan):
    end = (ngay_dau_tuan + timedelta(days=6)).isoformat()
    start = ngay_dau_tuan.isoformat()
    return sorted((task for task in danh_sach_cong_viec() if task['planned_date'] and start <= task['planned_date'] <= end),
        key=lambda task: (task['planned_date'], task['id']))


def dem_trang_thai(tasks):
    done = sum((task['status'] == 'Hoàn thành' for task in tasks))
    todo = sum((task['status'] == 'Chưa làm' for task in tasks))
    doing = len(tasks) - done - todo
    return dict(total=len(tasks), done=done, todo=todo, doing=doing, pending=todo + doing)


def thong_ke_du_an():
    tasks = danh_sach_cong_viec()
    return [dict(id=root['id'],
        name=root['name'],
        progress=root['progress'],
        **dem_trang_thai([task for task in tasks if task['root_id'] == root['id']])) for root in load_projects()]


def thong_ke_tong_quan(today=None):
    today = today or date.today()
    tasks = danh_sach_cong_viec()
    roots = load_projects()
    result = dem_trang_thai(tasks)
    result['projects'] = len(roots)
    result['progress'] = round(sum((root['progress'] for root in roots)) / len(roots), 1) if roots else 0
    result['overdue'] = sum((task['status'] != 'Hoàn thành' and bool(task['due_date']) and (task['due_date'] < today.isoformat()) for task in tasks))
    return result


def display_date(value):
    if not value:
        return 'Chưa đặt ngày'
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return 'Ngày cần cập nhật'


def database_error_message(error):
    """Chuyển lỗi kỹ thuật thành hướng dẫn tiếng Việt, không báo lưu giả."""
    code = getattr(error, 'sqlite_errorcode', None)
    if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
        return 'Dữ liệu đang được chương trình khác sử dụng. Hãy thử lại sau ít giây.'
    if code in (sqlite3.SQLITE_READONLY, sqlite3.SQLITE_CANTOPEN):
        return 'Không thể mở hoặc ghi planner.db. Hãy kiểm tra quyền ghi của thư mục ứng dụng.'
    return f'Không thể truy cập planner.db. Chi tiết SQLite: {error}'
