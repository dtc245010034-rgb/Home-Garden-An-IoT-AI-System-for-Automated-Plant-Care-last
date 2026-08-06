# Nhật ký đối chiếu báo cáo với hệ thống

Ngày rà soát: **06/08/2026** · Bản gốc lưu tại `SIC_IoT_Final_Report_SmartHomeGarden.BACKUP-20260806.docx`

Đối chiếu từng số liệu và từng phát biểu trong `SIC_IoT_Final_Report_SmartHomeGarden.docx`
với mã nguồn đang chạy (`main.py`, `firmware/v2/v2.ino`, `templates/dashboard.html`).
Tìm được 22 điểm lệch, đã áp 49 phép sửa vào file `.docx` mà không thay đổi định dạng
template. Mỗi dòng dưới đây ghi rõ báo cáo nói gì, thực tế là gì, và vì sao lệch.

---

## A · Sai số liệu

| # | Mục | Báo cáo viết | Thực tế trong code | Ghi chú |
|---|---|---|---|---|
| A1 | 2.2, 3.1 | Làm mịn quang trở: mới 0.7 / cũ 0.3 | `g_lightSmooth * 0.7 + rawLight * 0.3` → **cũ 0.7 / mới 0.3** | Đảo ngược trọng số. Bản báo cáo mô tả một bộ lọc phản ứng nhanh, code thì làm mịn mạnh |
| A2 | 3.1, 3.4 | Trường `mode` nhận `AUTO`, `MANUAL` hoặc `LOCKED` | `manualMode ? "MANUAL" : "AUTO"` — **không tồn tại `LOCKED`** | `LOCK_IDLE` được truyền về dưới dạng `MANUAL` với hai relay đều nhả |
| A3 | 2.4 | Firmware 355 dòng | `firmware/v2/v2.ino` = **432 dòng** | 355 là số dòng của **v1** — bảng đang mô tả bản cũ |
| A4 | 2.4 | Supervisor 1074 dòng | `main.py` = **1098 dòng** | Đếm trước khi thêm heartbeat và bộ lọc khung sự kiện |
| A5 | 2.2 | "một trong **năm** giá trị cho phép" | `VALID_AI_STATES` có **4** giá trị | `khong_xac_dinh` là giá trị dự phòng khi bị loại, không phải giá trị được phép |
| A6 | 2.2 | `normalize_ai_result()` thực hiện **4** kiểm tra | Hàm này thực hiện **3** | Kiểm tra "có cây trong khung" do prompt đảm nhiệm và `update_camera_health()` đếm, không nằm trong hàm chuẩn hoá |
| A9 | 3.1 | "đất dưới 40% → bật bơm" | `isDark && isDry` được xét **trước** và trả `MODE_IDLE`; `isDry && isHot` chọn phun sương | Bảng chính sách cục bộ bỏ mất thứ tự ưu tiên, đọc vào sẽ tưởng trời tối vẫn tưới |
| A10 | 3.3 | Camera đặt "phía trên khay" | `SETUP_PI5.md` quy định **chếch 45°**, cấm chụp thẳng đứng | Hai tài liệu nói trái nhau; chụp thẳng đứng làm bóng thân camera đổ lên lá |
| A11 | Hình 1.1, 2.1, 2.2, 2.3 | Nguồn hình: `smart_garden_diagrams.md` | File thật là `smart_garden_diagrams_v2.md` | 4 tham chiếu trỏ vào file không tồn tại |
| A12 | 3.5 · T1 | "6 phản hồi, **3 trong 6** đầu vào xấu bị loại" | Đo lại: **6/6** phản hồi xấu bị loại, 3/3 phản hồi hợp lệ được nhận | Câu gốc tự mâu thuẫn — nếu cả 6 đều xấu mà chỉ loại 3 thì test đã thất bại. Số mới lấy từ lần chạy thật `normalize_ai_result()` với 9 ca, tái lập được |
| A13 | 3.4 | "Bốn đồng hồ đo" cho nhiệt/ẩm/đất/sáng | 4 thẻ số + **1 đồng hồ vòng** riêng cho sức khoẻ AI | Bảng bỏ sót đồng hồ vòng, nhãn tin cậy, bảng ma trận fusion và khối điều khiển tay |
| A14 | 3.4 | Biểu đồ "cửa sổ 60 phút" | Chọn được 1 giờ / 6 giờ / 24 giờ / **7 ngày** | Trên 60 phút thì truy vấn SQLite và lấy mẫu thưa còn ≤ 300 điểm |
| A15 | 2.3 | Dashboard "poll mỗi 3 giây" | Trạng thái 3s · lịch sử 20s · sự kiện 30s · thống kê 60s | |

## B · Hệ thống có, báo cáo thiếu

| # | Mục | Nội dung bổ sung |
|---|---|---|
| B7 | 3.1 | Thêm hai trường `mist_locked` và `wd_tripped` vào bảng khung telemetry — firmware v2.1 đã phát cả hai |
| B8 | 3.1 | Thêm lệnh `PING` vào bảng tập lệnh |
| B16 | 2.3 | Thêm **watchdog serial** vào mục cơ chế an toàn. Đây là lớp bảo vệ khi Pi chết mà báo cáo bỏ trắng hoàn toàn, dù nó là thứ duy nhất ngăn bơm chạy đến hết nước |
| B17 | 2.3 | Thêm 4 hằng số: `PING_INTERVAL`, `SERIAL_WATCHDOG_MS`, `CAMERA_BLIND_THRESHOLD`, `ROOTROT_COOLDOWN` |
| B18 | 3.5 | Thêm 4 khiếm khuyết (số 10–13) tìm được ở lần rà soát thứ hai, kèm đoạn dẫn giải. Đổi header bảng từ "Defect in v1 / Correction in v2" thành "Defect / Correction" vì các dòng mới không thuộc v1 |
| B19 | 2.1 | Bảng hành vi khi lỗi từng phần nói "ESP32 quay về AUTO khi không còn lệnh" mà không nêu **nhờ đâu**. Nay ghi rõ: watchdog huỷ trạng thái sau 60 giây |
| B20 | 2.2 | Bổ sung: reader còn tách khung sự kiện của thiết bị khỏi khung telemetry |

## C · Phát biểu nay mới thật sự đứng vững

| # | Mục | Vấn đề |
|---|---|---|
| C21 | 4.1 · O5 | O5 khẳng định "khoá ban đêm không thể bị ghi đè" và đánh **Met**. Trước bản v2.2 điều này **sai**: watchdog huỷ `LOCK_IDLE` sau 60 giây vì supervisor không gửi heartbeat. Đã bổ sung bằng chứng heartbeat + watchdog vào ô Evidence |
| C22 | 3.5 · T5 | T5 kết luận "không tìm thấy định danh lệch". Đúng ở phạm vi định danh, nhưng không phủ được lỗi CSS. Đã thêm **T6** — kiểm tra render các phần tử có điều kiện |

---

## Bốn khiếm khuyết bổ sung vào mục 3.5

| # | Khiếm khuyết | Hậu quả | Cách sửa |
|---|---|---|---|
| 10 | Supervisor không gửi heartbeat mà firmware watchdog chờ. Do lệnh trùng bị lọc, một quyết định giữ nguyên không sinh byte nào trên serial | **Khoá ban đêm bị nhả sau ~60 giây** và có thể tưới trong tối — đúng thứ hệ thống cam kết là không thể ghi đè. Khoá thối rễ và override tay bị vô hiệu cùng cách | Gửi `PING` mỗi 10 giây. Đã test trên phần cứng thật |
| 11 | Khung sự kiện của thiết bị bị đọc như khung telemetry | Dashboard trắng số liệu và độ ẩm đất biến mất khỏi đầu vào fusion đúng lúc đang báo lỗi | Khung không có trường `temp` được đưa sang nhật ký sự kiện |
| 12 | Thuộc tính `hidden` vô tác dụng với mọi phần tử có khai báo `display` | 4 băng cảnh báo, lưới biểu đồ rỗng và khung ảnh hiện thường trực, trong đó một băng không có chữ nào | Thêm `[hidden]{display:none!important}`. Kiểm chứng hai chiều bằng render headless |
| 13 | Ghi chú AI chèn vào trang không escape; dấu thời gian ảnh đọc lệch 1 ký tự | Một dấu `<` trong ghi chú làm hỏng nhật ký; `14:30` hiện thành `_1:43` | Escape khi chèn; sửa offset |

---

## Việc còn lại cho người viết báo cáo

- Mục 1.4 chưa có dòng cho đợt rà soát 06/08. Nếu muốn thể hiện trong Gantt thì tự thêm phase 6, tôi không tự đặt mốc thời gian thay nhóm.
- Bộ sơ đồ `smart_garden_diagrams_v2.md` chưa vẽ `PING` và watchdog. Sơ đồ 1 và 4 nên bổ sung để khớp với phần 2.3 vừa sửa.
- Mục 3.5 vẫn còn `[ TBD — WBS item 3.3 ]` cho độ chính xác model. Con số này phải đo thật, không suy đoán được từ code.
- Các ô `[ TEAM NAME ]`, `[ Leader Name ]`, `[ Member 2..4 ]` và mục 5 vẫn để trống.

## Việc KHÔNG sửa

- Kết quả T2, T3, T4 giữ nguyên. Đó là số đo thực nghiệm của nhóm, không suy ra được từ code.
- Mức TRL 5 ở mục 4.1 giữ nguyên — đây là đánh giá, không phải sự kiện kiểm chứng được.
- `.docx` và `.xlsx` trong thư mục này **không đưa lên GitHub**: template mang ghi chú bản quyền của Samsung cấm sao chép lại, mà repo đang ở chế độ công khai. Xem `.gitignore`.
