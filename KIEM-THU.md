# Kiểm thử hệ thống

Vấn đề trung tâm: phần lớn chức năng chỉ kích hoạt trong những tình huống hiếm và
không gọi ra được theo ý muốn — cây héo rũ, đất sũng nước, lá nhiễm nấm, mất điện
giữa lúc bơm đang chạy. Ngồi chờ chúng xảy ra là không kiểm thử được.

Lời giải là nhận ra mọi điều kiện đó, khi đi vào phần mềm, chỉ còn là **dữ liệu
trong bộ nhớ**. Trạng thái AI là một dict. Độ ẩm đất là một số. Ban đêm là một hàm
trả về boolean. ESP32 là một đối tượng có `write()` và `readline()`. Dựng lại được
hết, không cần cây thật héo.

Tài liệu này mô tả ba tầng kiểm thử, từ nhanh nhất tới gần thực tế nhất.

## 1. Tầng logic — pytest, không cần phần cứng

45 bài, chạy trong khoảng một giây, không cần ESP32, camera, API key hay mạng.

```bash
python -m pip install pytest
python -m pytest tests -v
```

`tests/conftest.py` thay ba thư viện phần cứng (`cv2`, `serial`, `google.genai`)
bằng module giả trước khi import `main.py`, và trỏ dữ liệu vào thư mục tạm qua
`SG_DATA_DIR` nên không đụng `smart_garden.db` thật.

| File | Phủ |
|---|---|
| `test_kiem_chung_ai.py` | 8 dạng phản hồi hỏng của mô hình, 4 dạng hợp lệ, cảnh báo camera sau 3 lần |
| `test_ma_tran_fusion.py` | Đủ 10 ô của ma trận, cộng các trường hợp mất số liệu đất và số liệu quá cũ |
| `test_vong_lap_quyet_dinh.py` | Thứ tự năm mức, lọc lệnh trùng, nhịp PING, giới hạn thời hạn, đọc telemetry |

Điểm cần lưu ý về thiết kế: `test_vong_lap_quyet_dinh.py` gọi thẳng
`decision_tick()` của `main.py`. Bản đầu tiên chép lại logic vòng lặp vào test, hậu
quả là xoá `PING` khỏi mã thật mà cả bộ test vẫn xanh. Test chép lại code chỉ kiểm
tra chính bản chép, đó là niềm tin giả.

## 2. Bộ test có thật sự bắt được lỗi không

Test xanh không chứng minh điều gì nếu nó xanh cả khi mã hỏng. Cách kiểm chứng là
cố tình phá từng cơ chế rồi xem có bài nào đỏ lên không.

| Phép phá | Kết quả |
|---|---|
| Xoá lời gọi gửi `PING` | Bắt được |
| `PING_INTERVAL` 10 giây → 1 giờ | Bắt được |
| Bỏ lọc lệnh trùng của `MIST_LOCK` | Bắt được |
| Bỏ lọc lệnh trùng của `MIST_UNLOCK` | Bắt được |
| `SOIL_DRY_THRESHOLD` 40 → 0 | Bắt được |
| `AI_EMERGENCY_CONF` 70 → 5 | Bắt được |
| `AI_MIN_CONF` 40 → 0 | Bắt được |
| `EMERGENCY_WATER_DURATION` → vô hạn | Bắt được |
| Bỏ bộ lọc khung sự kiện ESP32 | Bắt được |
| Bỏ cảnh báo camera | Bắt được |
| Đưa Time Guard xuống dưới override tay | Bắt được |
| Nghi thối rễ nhưng vẫn tưới | Bắt được |

Quá trình này đã tìm ra ba lỗ hổng trong chính bộ test và cả ba đã được vá:
test chép lại vòng lặp; thiếu bất biến giữa `PING_INTERVAL` và watchdog; thiếu bài
cho nhánh dedupe của `MIST_LOCK`.

Muốn chạy lại kiểm thử đột biến thì sửa một hằng số trong `main.py`, chạy
`pytest tests`, xác nhận có bài đỏ, rồi hoàn tác.

## 3. Tầng kịch bản — diễn trên hệ thật

Dùng khi cần quay video minh hoạ hoặc kiểm tra đường đi đầy đủ tới ESP32 thật.
Chế độ này cho phép ép trạng thái AI qua HTTP nên **mặc định tắt**:

```bash
sudo systemctl stop smart-garden
cd ~/smart_garden
set -a && source /etc/smart-garden.env && set +a
SG_TEST_MODE=1 ./venv/bin/python main.py
```

Không đặt `SG_TEST_MODE` vào `/etc/smart-garden.env`. Ba endpoint dưới đây trả về
403 khi cờ tắt.

| Endpoint | Việc |
|---|---|
| `POST /api/test/ai` | Tiêm một chẩn đoán, đi qua đúng hàm kiểm chứng như chẩn đoán thật |
| `POST /api/test/night` | Ép hoặc bỏ ép khung giờ ban đêm |
| `POST /api/test/reset` | Xoá chẩn đoán tiêm, bộ đếm xung và ép giờ |

### Kịch bản 1 — Tưới khẩn cấp khi héo rũ, đất khô

Cần đất thật đang khô, hoặc rút đầu dò khỏi đất.

```bash
curl -X POST -H 'Content-Type: application/json' \
     -d '{"trang_thai":"heo_ru","do_tin_cay":95}' http://localhost:5000/api/test/ai
```

Trong vòng 2 giây: dashboard hiện băng đỏ "Đang tưới khẩn cấp" kèm đếm ngược, bơm
chạy, mức quyết định hiện `1-KHẨN CẤP`. Sau 60 giây bơm tự tắt và mức trở về
`5-MẶC ĐỊNH`.

### Kịch bản 2 — Nghi thối rễ, cùng triệu chứng nhưng ngược hành vi

Cần đất thật đang ẩm (tưới trước cho đất lên trên 40%), rồi tiêm đúng chẩn đoán
như kịch bản 1. Đây là cảnh đáng quay nhất: **cùng một đầu vào AI, hành vi ngược
lại**, và không hệ nào chỉ dùng cảm biến làm được.

Kết quả mong đợi: bơm **không** chạy, băng đỏ "Nghi thối rễ — đã khoá tưới" kèm
đếm ngược 15 phút.

### Kịch bản 3 — Time Guard chặn lệnh tay

```bash
curl -X POST -H 'Content-Type: application/json' -d '{"bat":true}' \
     http://localhost:5000/api/test/night
```

Rồi bấm "Bật tưới" trên dashboard. Lệnh được nhận và ghi log, nhưng vòng kế tiếp
hệ phát `LOCK_IDLE` đè lên. Mức quyết định hiện `2-TIME GUARD`.

### Kịch bản 4 — Cấm phun sương khi phát hiện nấm

```bash
curl -X POST -H 'Content-Type: application/json' \
     -d '{"trang_thai":"dom_nau","do_tin_cay":80}' http://localhost:5000/api/test/ai
```

Băng vàng "Phun sương đang bị khoá" hiện lên, nhãn phun sương chuyển `KHOÁ`, nhưng
tưới gốc vẫn chạy theo ngưỡng. Trên OLED của ESP32, dòng lý do đổi thành
`Kho + nong nhung SUONG BI KHOA (nam) - tuoi goc`.

### Kịch bản 5 — Watchdog khi Pi chết

Không cần chế độ kiểm thử. Bấm "Bật tưới" trên dashboard rồi rút cáp USB giữa Pi
và ESP32. Sau 60 giây ESP32 tự nhả relay và quay về AUTO. Cắm lại cáp, dashboard
hiện băng "ESP32 đã tự quay về AUTO".

Đây cũng là bài kiểm chứng cho bản vá `PING`: **trước** khi vá, chỉ cần giữ nguyên
lệnh 60 giây mà không rút cáp gì cả là watchdog cũng nổ.

Nhớ chạy `POST /api/test/reset` sau khi diễn xong, rồi khởi động lại service bình
thường bằng `sudo systemctl start smart-garden`.

## 4. Làm sao biết hệ đang chạy trơn tru

Gọi một lời:

```bash
curl -s http://localhost:5000/api/health | python3 -m json.tool
```

Trả `200` khi mọi thứ ổn hoặc chỉ có cảnh báo, `503` khi có mục ở mức `bad`. Năm
mục được kiểm: liên kết serial, chẩn đoán AI, camera, cơ sở dữ liệu, và số lỗi
trong một giờ qua. Mỗi mục kèm lý do bằng chữ.

Dùng cho giám sát định kỳ:

```bash
watch -n 30 'curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5000/api/health'
```

Ba dấu hiệu đáng tin khác, xem trực tiếp trên dashboard:

- Chấm trạng thái góc trên phải là xanh và ghi "Đang hoạt động". Vàng hoặc đỏ nghĩa
  là khung telemetry đang chậm hoặc đã mất.
- Dòng chân trang cho biết số bản ghi cảm biến. Con số này phải tăng khoảng
  60 bản ghi mỗi giờ. Đứng yên nghĩa là luồng đọc serial hoặc lớp ghi CSDL đã chết.
- Nhãn dưới vòng tròn sức khoẻ phải là "ĐỦ TIN CẬY". Liên tục "KHÔNG ĐỦ TIN CẬY"
  nghĩa là camera đang có vấn đề chứ không phải cây có vấn đề.

## 5. Lỗi được ghi ở đâu

Hệ thống ghi lỗi vào ba nơi, mỗi nơi phục vụ một mục đích khác nhau.

| Nơi ghi | Nội dung | Cách xem |
|---|---|---|
| Bảng `events` trong SQLite | Sự kiện có cấu trúc, truy vấn được, kèm traceback | `sqlite3 smart_garden.db` hoặc `GET /api/events` |
| `smart_garden_events.log` | Cùng nội dung, dạng JSON một dòng một bản ghi | `tail -f smart_garden_events.log` |
| journald | Toàn bộ stdout, gồm cả bảng trạng thái in mỗi 2 giây | `journalctl -u smart-garden -f` |

Các loại sự kiện đang được ghi: `startup`, `ai_diagnosis`, `emergency_watering`,
`camera_alert`, `manual_command`, `esp32_event`, `test_inject`, và `error`.

Truy vấn lỗi:

```sql
-- Lỗi gần nhất kèm nơi phát sinh và traceback
SELECT ts, json_extract(detail,'$.where')   AS o_dau,
           json_extract(detail,'$.message') AS thong_diep
FROM events WHERE event='error' ORDER BY epoch DESC LIMIT 20;

-- Đếm lỗi theo nơi phát sinh, để biết chỗ nào hay hỏng nhất
SELECT json_extract(detail,'$.where') AS o_dau, COUNT(*) AS so_lan
FROM events WHERE event='error' GROUP BY o_dau ORDER BY so_lan DESC;
```

Traceback đầy đủ nằm ở `json_extract(detail,'$.traceback')`.

### Hai điều cần biết về đường ghi lỗi

**Lỗi ghi SQLite không thể tự ghi vào SQLite.** Khi `db_exec()` hỏng, nó ghi thẳng
vào `smart_garden_events.log` thay vì gọi `log_event()` — gọi vòng lại chính lớp
đang hỏng thì sẽ đệ quy. Vậy nên khi nghi ngờ cơ sở dữ liệu có vấn đề, **file
JSON-lines mới là nơi còn dấu vết**, không phải bảng `events`.

**Bốn luồng đều bọc bắt lỗi ở vòng ngoài.** Trước đây `serial_reader` không có, nên
một ngoại lệ bất ngờ làm chết luồng trong im lặng: hệ vẫn chạy, dashboard vẫn mở,
nhưng số liệu đóng băng vĩnh viễn và chỉ lộ ra qua đồng hồ tuổi số liệu. Nay mọi
ngoại lệ đều được ghi kèm traceback và vòng lặp tiếp tục.

## 6. Việc kiểm thử này không phủ được

Nói thẳng để không nhầm phạm vi.

- **Phần cứng vật lý.** Relay có đóng thật không, bơm có ra nước không, đầu dò đọc
  có đúng không. Chỉ kiểm bằng tay được.
- **Chất lượng chẩn đoán của Gemini.** Bộ test kiểm chứng hệ thống **xử lý đúng**
  mọi dạng phản hồi, nhưng không nói được mô hình chẩn đoán chính xác đến đâu.
  Con số đó phải đo trên tập ảnh có gán nhãn.
- **Firmware ESP32.** Không có test tự động. Watchdog và logic `decideMode()` chỉ
  kiểm bằng kịch bản 5 và bằng cách quan sát OLED.
- **Hành vi dài ngày.** Đầu dò trôi giá trị, hơi nước đọng trên vỏ camera, thẻ nhớ
  đầy. Chỉ đợt chạy thực địa 3–5 ngày mới phơi ra được.
