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
| `weekly_calendar.py` | Điều phối Lịch mục tiêu, chọn ngày/tuần, thu gọn nhánh và thao tác với task. Giữ tên file/hàm cũ để không làm đứt callback. |
| `timeline.py` | Vẽ cây và các khoảng ngày trên Canvas, đồng bộ cuộn và hiển thị tiến độ. |
| `calendar_data.py` | Chuẩn bị cây, phân biệt task lá, lọc việc trong ngày/tuần và tính tỷ lệ theo ngày. |

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

Các giới hạn còn lại: chạy từ thư mục gốc; chưa xóa trống ngày đã lưu.
Biểu mẫu nay từ chối mở nếu ID cha được truyền vào không còn tồn tại.

## Sử dụng Lịch mục tiêu

1. Tạo mục tiêu với ngày bắt đầu A và ngày kết thúc B. Tab **Lịch mục tiêu**
   hiển thị một thanh phủ cả hai ngày A và B, cùng các công việc con ở những dòng riêng.
2. Nhấn tam giác cạnh tên để mở/thu gọn nhánh. Chọn tên hoặc thanh để xem đầy đủ
   tên, ngày và tiến độ. Dùng **+ Việc con**, **Sửa**, **Mở chi tiết** ở ngay dưới lịch.
   Nhấn đúp tên/thanh cũng mở biểu mẫu sửa.
3. Kéo thanh cuộn ngang để xem các tháng khác; kéo thanh cuộn dọc để xem nhiều task.
   Cột tên luôn cố định khi cuộn ngang. Giữ Shift khi cuộn chuột để dịch ngang.
   Nút **Hôm nay** đưa lịch về ngày hiện tại.
4. Chọn **Ngày** hoặc **Tuần**, rồi bấm một ô ở hàng ngày phía trên.
   Danh sách bên dưới chỉ lấy task lá có khoảng ngày giao với ngày/tuần đã chọn.
   Mặc định ẩn việc đã xong; đánh dấu **Cả việc đã xong** để xem lại.
5. Chọn **Chưa xếp lịch** để tìm task lá chưa có đủ hai ngày hoặc có ngày không hợp lệ.
   Chọn việc và bấm **Sửa** để bổ sung ngày. Task thiếu ngày không được tự gán thời gian.
   Mục tiêu chưa có con cũng được xem là task lá.
6. Chọn một việc trong bảng và bấm **Xong** để cập nhật `is_done`. Database tính lại
   tiến độ; cây, thanh thời gian, tỷ lệ ngày và các trang được tải lại cùng lúc.

Nền nhạt của thanh thể hiện khoảng thời gian dự kiến; dải màu bên trong biểu thị
`calc_progress(task_id)`. Dải tiến độ không có nghĩa là đã làm xong những ngày bên trái.
Task hoàn thành có màu xanh lá và dấu ✓. Đường xanh dọc đánh dấu hôm nay.

Tỷ lệ dưới mỗi ngày được tính riêng: số task lá đã xong phủ ngày đó / tổng số task lá
phủ ngày đó. Ví dụ 2/4 việc đã xong thì hiển thị 50%. Các task cha không được đếm lần nữa.
Ngày không có task lá được lên lịch hiển thị dấu —.

Đây là tiến độ hiện tại đối chiếu với lịch dự kiến. Bảng Task chưa lưu ngày hoàn thành
thực tế nên lịch không thể cho biết chính xác mỗi ngày trong quá khứ đã làm được gì.
Không thêm thư viện hay thay đổi schema. Lịch dùng Tkinter Canvas và chỉ vẽ các cột
ngày đang nhìn thấy để tránh tạo hàng nghìn ô khi mục tiêu kéo dài nhiều năm.
