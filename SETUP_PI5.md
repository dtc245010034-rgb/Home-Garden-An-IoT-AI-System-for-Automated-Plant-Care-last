# Hướng dẫn triển khai trên Raspberry Pi 5

Smart Home Garden v2 — SIC IoT Capstone
Thời gian ước tính: **25–35 phút** (lần đầu, tính cả thời gian tải gói).

---

## 0. Chuẩn bị

| Hạng mục | Yêu cầu |
|---|---|
| Hệ điều hành | Raspberry Pi OS **Bookworm** 64-bit (Debian 12) |
| Nguồn | Adapter chính hãng **27W USB-C** — Pi 5 cắm thêm webcam + ESP32 rất dễ sụt áp |
| Thẻ nhớ | ≥ 32GB, class A2 (SQLite ghi liên tục, thẻ rẻ dễ hỏng) |
| Mạng | Pi và máy xem dashboard phải **cùng một mạng LAN** |
| API key | Lấy miễn phí tại https://aistudio.google.com/apikey |

Kiểm tra phiên bản OS:

```bash
cat /etc/os-release | head -2
uname -m          # phải ra aarch64
```

> ⚠️ Nếu ra `armv7l` là bạn đang chạy bản 32-bit — `opencv-python-headless` sẽ
> không có sẵn bánh xe (wheel) biên dịch trước và pip sẽ cố build từ nguồn trong
> ~40 phút rồi hỏng. Hãy cài lại OS bản 64-bit.

---

## 1. Cấu trúc thư mục

Copy toàn bộ dự án vào `/home/pi/smart_garden` (đổi `pi` thành tên user của bạn):

```
/home/pi/smart_garden/
├── main.py                     ← chương trình chính
├── templates/
│   └── dashboard.html          ← BẮT BUỘC nằm trong templates/
├── deploy/
│   ├── install.sh              ← script cài tự động
│   └── smart-garden.service    ← file systemd
├── firmware/
│   └── v2/v2.ino               ← firmware ESP32 v2.1 (MIST_LOCK + watchdog)
├── doc/                        ← báo cáo, sơ đồ, nhật ký đối chiếu
├── SETUP_PI5.md                ← file này
├── photos/                     ← tự tạo khi chạy
└── smart_garden.db             ← tự tạo khi chạy
```

Copy từ máy tính sang Pi qua mạng LAN:

```bash
# Chạy trên máy tính của bạn, không phải trên Pi
scp -r smart_garden pi@<IP_CUA_PI>:~/
```

---

## 2. Cài đặt tự động (khuyến nghị)

```bash
cd ~/smart_garden
bash deploy/install.sh
```

Script sẽ tự làm 8 bước: cài gói hệ thống → cấp quyền `dialout`/`video` →
tạo tên cổng cố định `/dev/esp32` → tạo virtualenv → cài thư viện Python →
hỏi API key → cài systemd service → khởi động.

Khi được hỏi, dán `GEMINI_API_KEY` vào rồi Enter.

**Sau khi xong, đăng xuất và đăng nhập lại một lần** để quyền nhóm `dialout` có
hiệu lực (hoặc đơn giản là `sudo reboot`).

---

## 3. Cài đặt thủ công (nếu muốn hiểu từng bước)

<details>
<summary>Bấm để mở phần cài thủ công</summary>

```bash
# 3.1 — Gói hệ thống
sudo apt update
sudo apt install -y python3-venv python3-dev libgl1 libglib2.0-0 \
                    libatlas-base-dev v4l-utils sqlite3

# 3.2 — Quyền truy cập cổng serial và camera
sudo usermod -aG dialout,video $USER

# 3.3 — Môi trường ảo Python
cd ~/smart_garden
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install flask pyserial opencv-python-headless google-genai

# 3.4 — Biến môi trường (chmod 600 để API key không lộ)
sudo tee /etc/smart-garden.env >/dev/null <<'EOF'
GEMINI_API_KEY=dan_key_cua_ban_vao_day
SG_SERIAL_PORT=/dev/esp32
SG_CAM_INDEX=0
SG_PORT=5000
SG_MODEL=gemini-3.1-flash-lite
EOF
sudo chmod 600 /etc/smart-garden.env

# 3.5 — systemd
sudo cp deploy/smart-garden.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smart-garden
```

</details>

---

## 4. Xác minh phần cứng trước khi chạy

### 4.1 Cổng serial ESP32

```bash
ls -l /dev/esp32
# Kết quả mong đợi:  lrwxrwxrwx 1 root root 7 ... /dev/esp32 -> ttyUSB0
```

Nếu **không có** `/dev/esp32`, tìm VID:PID thật của board bạn:

```bash
lsusb | grep -iE 'cp210|ch340|serial'
# Ví dụ: Bus 001 Device 005: ID 1a86:7523 QinHeng CH340
```

Rồi thêm dòng tương ứng vào `/etc/udev/rules.d/99-smart-garden.rules` với đúng
`idVendor`/`idProduct` vừa tìm được, sau đó:

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Đọc thử dữ liệu ESP32 đang gửi lên:

```bash
sudo apt install -y python3-serial
python3 -m serial.tools.miniterm /dev/esp32 115200
# Phải thấy dòng JSON mỗi 2 giây:
# {"temp":28.4,"humi":72,"soil":35,"light":48,"water":true,...}
# Thoát bằng Ctrl + ]
```

### 4.2 Camera

```bash
v4l2-ctl --list-devices
ls /dev/video*
```

Pi 5 thường liệt kê **nhiều** `/dev/videoN` cho cùng một webcam (video0 là luồng
ảnh, video1 là kênh metadata). Nếu `SG_CAM_INDEX=0` chụp ra ảnh đen, thử index khác:

```bash
cd ~/smart_garden
for i in 0 1 2; do
  ./venv/bin/python -c "
import cv2
c=cv2.VideoCapture($i)
ok,f=c.read(); c.release()
print('index $i ->', 'OK' if ok else 'KHONG DOC DUOC', f.shape if ok else '')
"
done
```

Index nào báo `OK` kèm kích thước ảnh (ví dụ `(720, 1280, 3)`) thì sửa lại
`SG_CAM_INDEX` trong `/etc/smart-garden.env`.

---

## 5. Đặt camera cho đúng — bước quyết định điểm số

Đây là **Blocker 1** trong bản đánh giá trước: log ngày 01/08 cho thấy toàn bộ
7 lần chẩn đoán đều trả về *"ảnh chụp lớp học với máy tính xách tay"*. Phần mềm v2
đã biết **kêu lên** khi gặp tình trạng này, nhưng chỉ bạn mới sửa được nguyên nhân.

**Quy tắc đặt camera:**

| Yếu tố | Khuyến nghị |
|---|---|
| Khoảng cách | 25–40 cm tính từ ống kính tới tán lá |
| Góc | Chếch **45°** từ trên xuống, không chụp thẳng đứng (tránh bóng thân camera đổ lên lá) |
| Khung hình | Lá phải chiếm **≥ 60%** diện tích ảnh. Không lọt bàn, tường, mặt người vào khung |
| Ánh sáng | Tránh ngược sáng cửa sổ. Nếu chụp ban đêm phải có đèn LED trắng ~5000K |
| Nền | Đặt tấm bìa trắng hoặc đen phía sau khay rau — nền sạch giúp AI tăng độ tin cậy rõ rệt |
| Cố định | Dùng giá đỡ hoặc kẹp. Camera bị xê dịch = toàn bộ dữ liệu chuỗi thời gian mất giá trị |

**Kiểm tra ngay sau khi đặt:**

1. Mở dashboard, bấm nút **"📷 Chụp & chẩn đoán ngay (CHECK_LEAF)"**.
2. Nhìn nhãn ngay dưới vòng tròn sức khoẻ:
   - ✅ `ĐỦ TIN CẬY ĐỂ RA QUYẾT ĐỊNH` → camera đã đúng, xong việc.
   - ❌ `KHÔNG ĐỦ TIN CẬY — BỎ QUA AI` → đọc dòng ghi chú của AI ngay bên trên,
     nó nói rõ đang nhìn thấy gì. Chỉnh lại camera và chụp lại.
3. Lặp lại tới khi độ tin cậy đạt **≥ 70%** với cây khoẻ.

> Sau 3 lần liên tiếp không nhận diện được cây, dashboard sẽ hiện băng đỏ
> *"Cảnh báo camera"* và ghi sự kiện `camera_alert` vào cơ sở dữ liệu. Trong buổi
> bảo vệ, băng cảnh báo này thực ra là **điểm cộng** — nó chứng minh hệ thống biết
> tự phát hiện lỗi thay vì im lặng báo sai.

---

## 6. Vận hành hằng ngày

```bash
# Xem log thời gian thực (giống hệt khi chạy tay trong terminal)
sudo journalctl -u smart-garden -f

# Chỉ xem lỗi
sudo journalctl -u smart-garden -p err --since today

# Khởi động lại sau khi sửa code
sudo systemctl restart smart-garden

# Dừng hẳn (bắt buộc làm trước khi nạp firmware ESP32)
sudo systemctl stop smart-garden

# Xem service có tự khởi động cùng máy không
systemctl is-enabled smart-garden
```

### Chạy tay để gỡ lỗi (có nhập lệnh bằng bàn phím)

Service systemd không nhận input bàn phím. Muốn gõ `CHECK_LEAF`, `WATER_ON`…
trực tiếp thì phải dừng service trước:

```bash
sudo systemctl stop smart-garden
cd ~/smart_garden
set -a && source /etc/smart-garden.env && set +a
./venv/bin/python main.py
```

---

## 7. Truy vấn dữ liệu cho báo cáo

Toàn bộ dữ liệu nằm trong `smart_garden.db`. Đây là nguồn số liệu cho **mục 3.4
Data Visualization** và **3.5 Testing and Improvements** của Final Report.

```bash
cd ~/smart_garden
sqlite3 smart_garden.db
```

```sql
-- Số bản ghi đã thu thập và khoảng thời gian
SELECT COUNT(*) AS so_ban_ghi, MIN(ts) AS bat_dau, MAX(ts) AS ket_thuc
FROM sensor_readings;

-- Độ chính xác AI: bao nhiêu % lần chẩn đoán đạt ngưỡng tin cậy
SELECT COUNT(*) AS tong,
       SUM(trusted) AS dang_tin,
       ROUND(100.0 * SUM(trusted) / COUNT(*), 1) AS ty_le_phan_tram
FROM ai_diagnosis;

-- Phân bố các trạng thái AI phát hiện được
SELECT trang_thai, COUNT(*) AS so_lan, ROUND(AVG(do_tin_cay),1) AS tin_cay_tb
FROM ai_diagnosis WHERE trusted = 1
GROUP BY trang_thai ORDER BY so_lan DESC;

-- Nhật ký các lần tưới khẩn cấp (dùng làm bằng chứng kiểm thử)
SELECT ts, detail FROM events WHERE event = 'emergency_watering' ORDER BY epoch DESC;

-- Kiểm chứng ma trận fusion: lệnh nào được gửi ở mức ưu tiên nào
SELECT level, cmd, COUNT(*) AS so_lan FROM commands GROUP BY level, cmd ORDER BY so_lan DESC;

-- Nhiệt độ / độ ẩm đất trung bình theo giờ (vẽ biểu đồ trong báo cáo)
SELECT substr(ts,1,13) AS gio,
       ROUND(AVG(temp),1) AS nhiet_do,
       ROUND(AVG(soil),1) AS am_dat
FROM sensor_readings GROUP BY gio ORDER BY gio;
```

Thoát bằng `.quit`.

**Xuất CSV để vẽ biểu đồ trong Excel / Google Sheets:**

- Trên dashboard: bấm nút **"Tải CSV 24h"** ở thẻ Nhật ký hệ thống.
- Hoặc gọi trực tiếp: `http://<IP_PI>:5000/api/export.csv?hours=168` (7 ngày).

---

## 8. Xử lý sự cố

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Service `failed`, log ghi *"Thiếu biến môi trường GEMINI_API_KEY"* | Sai đường dẫn `EnvironmentFile` hoặc file rỗng | `sudo cat /etc/smart-garden.env` kiểm tra, rồi `sudo systemctl restart smart-garden` |
| Log lặp *"Không tìm thấy /dev/esp32"* | Chưa cắm ESP32, hoặc udev rule chưa khớp chip | Xem lại mục 4.1 |
| `Permission denied: '/dev/ttyUSB0'` | User chưa vào nhóm `dialout` | `sudo usermod -aG dialout $USER` rồi **reboot** |
| Ảnh chụp ra toàn màu đen | Sai `SG_CAM_INDEX`, hoặc webcam cần thời gian tự động phơi sáng | Thử index khác (mục 4.2). Code đã bỏ 6 khung đầu, nếu vẫn đen thì tăng `CAM_WARMUP_FRAMES` trong `main.py` |
| `[Errno -3] Temporary failure in name resolution` | Pi mất Internet | Hệ thống vẫn chạy bình thường theo cảm biến, chỉ mất chức năng AI. Kiểm tra WiFi/DNS: `ping -c2 8.8.8.8` |
| Dashboard mở được trên Pi nhưng máy khác không vào được | Khác mạng LAN, hoặc firewall | Kiểm tra `hostname -I` và bảo đảm hai máy cùng dải IP. Nếu bật ufw: `sudo ufw allow 5000/tcp` |
| Arduino IDE báo *"port busy"* khi nạp firmware | `main.py` đang giữ cổng | `sudo systemctl stop smart-garden` trước khi nạp |
| Biểu đồ trống sau khi restart | *(Đã sửa ở v2)* — nếu vẫn trống thì cơ sở dữ liệu chưa có đủ 2 điểm | Chờ 2 phút, hệ thống ghi SQLite mỗi 60 giây |
| Thẻ nhớ đầy | Kho ảnh hoặc log journald phình to | Kho ảnh đã tự giới hạn 50 file. Giới hạn journald: `sudo journalctl --vacuum-size=200M` |

---

## 9. Nội dung đã thay đổi so với v1

Ghi lại đây để bạn viết vào **mục 3.5 Testing and Improvements** của báo cáo.

| # | Vấn đề ở v1 | Cách sửa ở v2 |
|---|---|---|
| 1 | Camera chĩa sai chỗ nhưng hệ thống im lặng báo "bình thường" | Prompt AI có bước kiểm tra ảnh có cây hay không; đếm chuỗi thất bại liên tiếp; băng cảnh báo đỏ trên dashboard; ghi sự kiện `camera_alert` |
| 2 | Chấp nhận `binh_thuong` với `do_tin_cay = 0`; nhận trạng thái ngoài enum | Hàm `normalize_ai_result()` kiểm chứng enum + ngưỡng `AI_MIN_CONF = 40`; kết quả không đạt bị hạ xuống `khong_xac_dinh` và **không được phép** tác động cơ cấu chấp hành |
| 3 | Bơm có thể bật vô thời hạn trong 1 giờ cooldown | Cơ chế `pulse()` dùng chung: mọi lệnh ép actuator đều có thời hạn. Tưới khẩn cấp 60 giây rồi tự trả `AUTO` |
| 4 | Lịch sử cảm biến chỉ nằm trong RAM, mất khi restart | SQLite chế độ WAL, ghi mỗi 60 giây, tự nạp lại 60 phút gần nhất khi khởi động |
| 5 | Event log chỉ ghi sự kiện AI, không có số liệu cảm biến | 4 bảng: `sensor_readings`, `ai_diagnosis`, `commands`, `events` + endpoint xuất CSV |
| 6 | Ảnh bị ghi đè, không truy vết được | Lưu `photos/leaf_YYYYmmdd_HHMMSS.jpg`, tự giữ 50 file mới nhất, dashboard có dải ảnh thu nhỏ kèm nhãn chẩn đoán |
| 7 | AI chỉ tác động 1/4 trạng thái, còn lại chỉ ghi log | Ma trận quyết định AI × độ ẩm đất; ba ô thay đổi hành vi thật: tưới khẩn cấp có điều kiện, khoá tưới khi nghi thối rễ, cấm phun sương khi phát hiện nấm |
| 8 | Chạy tay, log cho thấy 6 lần khởi động rải rác | systemd với `Restart=always`, `RestartSec=10`, tự chạy khi cắm điện |
| 9 | Tên cổng đổi giữa `ttyUSB0`/`ttyUSB1` | udev rule tạo tên cố định `/dev/esp32` |

Bốn khiếm khuyết tìm thêm ở lần rà soát ngày 06/08, khi đọc firmware và `main.py`
đối chiếu với nhau thay vì đọc riêng từng bên:

| # | Vấn đề | Cách sửa |
|---|---|---|
| 10 | `main.py` không gửi heartbeat mà watchdog firmware chờ. Do lệnh trùng bị lọc, quyết định giữ nguyên không sinh byte nào → **khoá ban đêm bị nhả sau ~60 giây**, có thể tưới trong tối | Gửi `PING` mỗi 10 giây trong `decision_loop` |
| 11 | Khung sự kiện của ESP32 bị đọc như khung cảm biến, xoá sạch số liệu trên dashboard | Bỏ qua khung không có trường `temp`, ghi sang nhật ký sự kiện |
| 12 | Thuộc tính `hidden` vô tác dụng với phần tử có khai báo `display` → 4 băng cảnh báo hiện thường trực | Thêm `[hidden]{display:none!important}` |
| 13 | Ghi chú AI chèn vào trang không escape; giờ trên thumbnail lệch 1 ký tự | Escape khi chèn; sửa offset `slice` |

---

## 10. Việc còn lại trước buổi bảo vệ

- [ ] Đặt lại camera và xác nhận nhãn **"ĐỦ TIN CẬY"** (mục 5) — quan trọng nhất
- [ ] Nạp firmware `firmware/v2/v2.ino` để `MIST_LOCK` và watchdog serial có tác dụng
- [ ] Cho hệ thống chạy liên tục **3–5 ngày** để có dữ liệu thật cho biểu đồ báo cáo
- [ ] Quay video 3 kịch bản kiểm thử: (a) tưới khẩn cấp, (b) Time Guard ban đêm, (c) cấm phun sương khi đốm nâu
- [ ] Chụp ảnh màn hình dashboard ở trạng thái có dữ liệu đầy đủ để đưa vào mục 3.4
- [ ] Chạy các câu truy vấn ở mục 7, chép kết quả vào mục 3.5
- [ ] Thêm xác thực cho `/api/command` — hiện bất kỳ ai trong LAN đều bật được bơm.
      Nếu không kịp làm, hãy nêu thẳng ở **mục 4.2 Future Improvements**; nêu ra
      được điểm yếu của chính mình luôn ăn điểm hơn là để giám khảo phát hiện.
