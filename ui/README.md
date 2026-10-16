# Cách đọc và chỉnh sửa giao diện

Chạy ứng dụng từ thư mục gốc:

```powershell
python main.py
```

Lệnh cũ `python -m ui.interface` vẫn chuyển đến cùng hàm `main()`.
Import module chỉ nạp các hàm, không mở cửa sổ hay tạo database.

## Mỗi file phụ trách việc gì?

| File | Trách nhiệm |
| --- | --- |
| `../main.py` | Dựng cửa sổ → khởi tạo database → tải dữ liệu → chạy `mainloop()`; báo lỗi khởi động và đóng cửa sổ nếu cần. |
| `interface.py` | Dựng bố cục chính, đặt widget và gắn callback cho nút. |
| `widgets.py` | Màu sắc, font, style và hàm tạo nhãn, nút, bảng dùng chung. |
| `state.py` | Giữ các widget, task đang chọn và tuần đang xem để các module dùng chung. |
| `actions.py` | Xử lý thao tác: chọn, mở, xóa, hoàn thành, quay về cha, chuyển tab, tải lại dữ liệu. |
| `forms.py` | Tạo biểu mẫu thêm dự án và thêm/sửa công việc; kiểm tra kết quả lưu để hiển thị lỗi. |
| `data.py` | Kiểm tra dữ liệu nhập, đổi ngày, gọi các hàm trong `database`, chuyển dữ liệu để widget hiển thị và tổng hợp thống kê. |
| `statistics.py` | Dựng và cập nhật trang thống kê. |
| `weekly_calendar.py` | Dựng lịch tuần, chọn ngày, chuyển tuần và hiển thị công việc theo ngày. |

## Ví dụ: bấm Lưu công việc

1. `forms.py` đọc tên, mô tả và ngày từ các ô nhập.
2. `data.them_cong_viec()` hoặc `data.sua_cong_viec()` kiểm tra dữ liệu.
3. Hàm đó gọi `database.insert_task()` hoặc `database.update_task()` để lưu vào bảng `Task`.
4. Sau khi lưu thành công, biểu mẫu gọi `actions.lam_moi_du_lieu()` để tải lại các trang.

`main.py` điều phối khởi động. Các callback của Tkinter tiếp tục xử lý thao tác khi `mainloop()` đang chạy.
Không cần chuyển toàn bộ xử lý nút bấm vào `main.py`.

## Vì sao dùng `state`?

Ví dụ `state.selected_project_id` là ID task đang xem. Các module đọc cùng một biến
qua `from ui import state`, rồi truy cập bằng `state.selected_project_id`.
Không dùng `from ui.state import selected_project_id`: gán lại tên được import
sẽ không cập nhật biến trong module `state`.

Các hàm trong `actions.py` import biểu mẫu và các trang tại nơi cần gọi.
Cách này tránh việc hai module phải nạp lẫn nhau khi khởi động.
Các tên hàm database và tham số của chúng được giữ nguyên.

## Kiểm thử và giới hạn

```powershell
python -B -m unittest test_ui -v
```

Kiểm thử tạo database trong thư mục tạm và dùng cửa sổ Tkinter ẩn.
Không chạy kiểm thử ghi trên `planner.db` thật.

Các giới hạn cũ vẫn còn: chạy từ thư mục gốc; chưa xóa trống ngày đã lưu;
biểu mẫu có thể chọn nhầm dự án nếu ID cha truyền vào không còn tồn tại.
Lần thay đổi này tập trung tách code, chưa sửa các hành vi đó.
