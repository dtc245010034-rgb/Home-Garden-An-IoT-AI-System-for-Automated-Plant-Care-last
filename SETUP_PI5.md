# Triển khai trên Raspberry Pi 5

Hướng dẫn cài đặt, xác minh phần cứng, vận hành và xử lý sự cố cho Smart Home Garden.
Lần đầu mất khoảng 25–35 phút, phần lớn là thời gian tải gói.

## 1. Yêu cầu

| Hạng mục | Yêu cầu |
|---|---|
| Hệ điều hành | Raspberry Pi OS Bookworm 64-bit (Debian 12) |
| Nguồn | Adapter chính hãng 27W USB-C. Pi 5 cắm thêm webcam và ESP32 rất dễ sụt áp |
| Thẻ nhớ | Từ 32 GB, class A2. SQLite ghi liên tục nên thẻ rẻ nhanh hỏng |
| Mạng | Pi và máy xem dashboard phải cùng một mạng LAN |
| API key | Lấy miễn phí tại https://aistudio.google.com/apikey |

```bash
cat /etc/os-release | head -2
uname -m          # phải ra aarch64
```

Nếu ra `armv7l` thì đang chạy bản 32-bit. `opencv-python-headless` không có wheel
biên dịch sẵn cho kiến trúc này, pip sẽ cố build từ nguồn khoảng 40 phút rồi hỏng.
Cài lại OS bản 64-bit.

## 2. Cấu trúc thư mục trên Pi

Đặt toàn bộ dự án vào `/home/pi/smart_garden`, đổi `pi` thành tên người dùng thật:

```
/home/pi/smart_garden/
├── main.py
├── templates/dashboard.html     bắt buộc nằm trong templates/
├── deploy/
│   ├── install.sh
│   └── smart-garden.service
├── firmware/v2/v2.ino
├── doc/
├── SETUP_PI5.md
├── photos/                      tự tạo khi chạy
└── smart_garden.db              tự tạo khi chạy
```

Chép từ máy tính sang Pi qua LAN:

```bash
scp -r smart_garden pi@<IP_CUA_PI>:~/
```

## 3. Cài đặt tự động

```bash
cd ~/smart_garden
bash deploy/install.sh
```

Script làm tám bước: cài gói hệ thống, cấp quyền `dialout` và `video`, tạo tên cổng
cố định `/dev/esp32`, tạo virtualenv, cài thư viện Python, hỏi API key, cài systemd
service, khởi động. Khi được hỏi thì dán `GEMINI_API_KEY` vào rồi Enter.

Xong thì đăng xuất đăng nhập lại, hoặc `sudo reboot`, để quyền nhóm `dialout` có
hiệu lực.

## 4. Cài đặt thủ công

<details>
<summary>Mở phần cài thủ công</summary>

```bash
# 4.1 Gói hệ thống
sudo apt update
sudo apt install -y python3-venv python3-dev libgl1 libglib2.0-0 \
                    libatlas-base-dev v4l-utils sqlite3

# 4.2 Quyền truy cập cổng serial và camera
sudo usermod -aG dialout,video $USER

# 4.3 Môi trường ảo Python
cd ~/smart_garden
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 4.4 Biến môi trường, chmod 600 để API key không lộ
sudo tee /etc/smart-garden.env >/dev/null <<'EOF'
GEMINI_API_KEY=dan_key_cua_ban_vao_day
SG_SERIAL_PORT=/dev/esp32
SG_CAM_INDEX=0
SG_PORT=5000
SG_MODEL=gemini-3.1-flash-lite
EOF
sudo chmod 600 /etc/smart-garden.env

# 4.5 systemd
sudo cp deploy/smart-garden.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smart-garden
```

</details>

## 5. Xác minh phần cứng

### 5.1 Cổng serial

```bash
ls -l /dev/esp32
# mong đợi: lrwxrwxrwx 1 root root 7 ... /dev/esp32 -> ttyUSB0
```

Không thấy `/dev/esp32` thì tìm VID:PID thật của board:

```bash
lsusb | grep -iE 'cp210|ch340|serial'
# ví dụ: Bus 001 Device 005: ID 1a86:7523 QinHeng CH340
```

Thêm dòng tương ứng vào `/etc/udev/rules.d/99-smart-garden.rules` với đúng
`idVendor` và `idProduct` vừa tìm được, rồi nạp lại:

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Đọc thử dữ liệu ESP32 đang gửi lên:

```bash
sudo apt install -y python3-serial
python3 -m serial.tools.miniterm /dev/esp32 115200
# phải thấy một dòng JSON mỗi 2 giây:
# {"temp":28.4,"humi":72,"soil":35,"light":48,"water":true,...}
# thoát bằng Ctrl + ]
```

### 5.2 Camera

```bash
v4l2-ctl --list-devices
ls /dev/video*
```

Pi 5 thường liệt kê nhiều `/dev/videoN` cho cùng một webcam: `video0` là luồng ảnh,
`video1` là kênh metadata. Nếu `SG_CAM_INDEX=0` chụp ra ảnh đen thì dò index khác:

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

Index nào báo `OK` kèm kích thước ảnh, ví dụ `(720, 1280, 3)`, thì sửa
`SG_CAM_INDEX` trong `/etc/smart-garden.env`.

## 6. Đặt camera

Chất lượng dữ liệu AI phụ thuộc gần như hoàn toàn vào bước này, và phần mềm không
sửa được. Log ngày 01/08 cho thấy cả 7 lần chẩn đoán đều trả về mô tả một lớp học
với máy tính xách tay, vì camera chĩa nhầm hướng. Bản v2 biết phát cảnh báo khi gặp
tình trạng này nhưng không tự khắc phục được nguyên nhân.

| Yếu tố | Yêu cầu |
|---|---|
| Khoảng cách | 25–40 cm từ ống kính tới tán lá |
| Góc | Chếch 45° từ trên xuống. Không chụp thẳng đứng, bóng thân camera sẽ đổ lên lá |
| Khung hình | Lá chiếm từ 60% diện tích. Không để bàn, tường, mặt người lọt vào |
| Ánh sáng | Tránh ngược sáng cửa sổ. Chụp ban đêm cần đèn LED trắng khoảng 5000K |
| Nền | Bìa trắng hoặc đen phía sau khay rau. Nền sạch làm độ tin cậy tăng rõ rệt |
| Cố định | Dùng giá đỡ hoặc kẹp. Camera xê dịch làm mất giá trị toàn bộ chuỗi thời gian |

Kiểm tra ngay sau khi đặt:

1. Mở dashboard, bấm nút "Chụp và chẩn đoán ngay".
2. Đọc nhãn ngay dưới vòng tròn sức khoẻ. Nhãn "ĐỦ TIN CẬY ĐỂ RA QUYẾT ĐỊNH" là
   đạt. Nhãn "KHÔNG ĐỦ TIN CẬY — BỎ QUA AI" thì đọc dòng ghi chú của AI phía trên,
   nó nói rõ đang nhìn thấy gì, rồi chỉnh lại camera và chụp lại.
3. Lặp cho tới khi độ tin cậy đạt từ 70% với cây khoẻ.

Sau ba lần liên tiếp không nhận diện được cây, dashboard hiện băng cảnh báo và ghi
sự kiện `camera_alert` vào cơ sở dữ liệu.

## 7. Vận hành

```bash
sudo journalctl -u smart-garden -f              # log thời gian thực
sudo journalctl -u smart-garden -p err --since today
sudo systemctl restart smart-garden
sudo systemctl stop smart-garden                # bắt buộc trước khi nạp firmware
systemctl is-enabled smart-garden
```

Service systemd không nhận input bàn phím. Muốn gõ trực tiếp `CHECK_LEAF`,
`WATER_ON` thì phải dừng service trước:

```bash
sudo systemctl stop smart-garden
cd ~/smart_garden
set -a && source /etc/smart-garden.env && set +a
./venv/bin/python main.py
```

## 8. Truy vấn dữ liệu cho báo cáo

Toàn bộ dữ liệu nằm trong `smart_garden.db`, là nguồn số liệu cho mục 3.4 Data
Visualization và 3.5 Testing and Improvements của Final Report.

```bash
cd ~/smart_garden
sqlite3 smart_garden.db
```

```sql
-- Số bản ghi và khoảng thời gian đã thu thập
SELECT COUNT(*) AS so_ban_ghi, MIN(ts) AS bat_dau, MAX(ts) AS ket_thuc
FROM sensor_readings;

-- Tỷ lệ chẩn đoán đạt ngưỡng tin cậy
SELECT COUNT(*) AS tong,
       SUM(trusted) AS dang_tin,
       ROUND(100.0 * SUM(trusted) / COUNT(*), 1) AS ty_le_phan_tram
FROM ai_diagnosis;

-- Phân bố các trạng thái AI phát hiện được
SELECT trang_thai, COUNT(*) AS so_lan, ROUND(AVG(do_tin_cay),1) AS tin_cay_tb
FROM ai_diagnosis WHERE trusted = 1
GROUP BY trang_thai ORDER BY so_lan DESC;

-- Nhật ký các lần tưới khẩn cấp, dùng làm bằng chứng kiểm thử
SELECT ts, detail FROM events WHERE event = 'emergency_watering' ORDER BY epoch DESC;

-- Kiểm chứng ma trận fusion: lệnh nào được gửi ở mức ưu tiên nào
SELECT level, cmd, COUNT(*) AS so_lan FROM commands
GROUP BY level, cmd ORDER BY so_lan DESC;

-- Sự kiện watchdog, nếu có, cho thấy đã từng mất liên lạc serial
SELECT ts, detail FROM events WHERE event = 'esp32_event' ORDER BY epoch DESC;

-- Nhiệt độ và độ ẩm đất trung bình theo giờ
SELECT substr(ts,1,13) AS gio,
       ROUND(AVG(temp),1) AS nhiet_do,
       ROUND(AVG(soil),1) AS am_dat
FROM sensor_readings GROUP BY gio ORDER BY gio;
```

Xuất CSV để vẽ biểu đồ ngoài: bấm "Tải CSV 24h" trên dashboard, hoặc gọi trực tiếp
`http://<IP_PI>:5000/api/export.csv?hours=168` cho 7 ngày.

## 9. Xử lý sự cố

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Service `failed`, log ghi "Thiếu biến môi trường GEMINI_API_KEY" | Sai đường dẫn `EnvironmentFile` hoặc file rỗng | `sudo cat /etc/smart-garden.env` kiểm tra rồi restart |
| Log lặp "Không tìm thấy /dev/esp32" | Chưa cắm ESP32, hoặc udev rule chưa khớp chip | Xem mục 5.1 |
| `Permission denied: '/dev/ttyUSB0'` | Người dùng chưa vào nhóm `dialout` | `sudo usermod -aG dialout $USER` rồi reboot |
| Ảnh chụp ra toàn đen | Sai `SG_CAM_INDEX`, hoặc webcam cần thời gian tự phơi sáng | Dò index theo mục 5.2. Code đã bỏ 6 khung đầu; vẫn đen thì tăng `CAM_WARMUP_FRAMES` |
| `[Errno -3] Temporary failure in name resolution` | Pi mất Internet | Hệ thống vẫn tưới theo cảm biến, chỉ mất tầng AI. Kiểm tra `ping -c2 8.8.8.8` |
| Dashboard mở được trên Pi nhưng máy khác không vào được | Khác dải mạng, hoặc firewall | Kiểm tra `hostname -I`. Nếu bật ufw thì `sudo ufw allow 5000/tcp` |
| Arduino IDE báo port busy khi nạp firmware | `main.py` đang giữ cổng | `sudo systemctl stop smart-garden` trước khi nạp |
| Biểu đồ trống sau khi restart | Cơ sở dữ liệu chưa có đủ 2 điểm | Chờ 2 phút, hệ thống ghi SQLite mỗi 60 giây |
| Dashboard hiện băng "ESP32 đã tự quay về AUTO" | Watchdog serial đã kích hoạt: quá 60 giây ESP32 không nhận được gì từ Pi | Kiểm tra cáp USB và `journalctl -u smart-garden`. Nếu service vẫn chạy bình thường mà băng này xuất hiện thì cáp hoặc cổng USB có vấn đề |
| Thẻ nhớ đầy | Kho ảnh hoặc log journald phình to | Kho ảnh tự giới hạn 50 file. Giới hạn journald: `sudo journalctl --vacuum-size=200M` |

## 10. Thay đổi so với v1

Dùng cho mục 3.5 Testing and Improvements của Final Report.

| # | Vấn đề | Cách sửa |
|---|---|---|
| 1 | Camera chĩa sai chỗ nhưng hệ thống im lặng báo bình thường | Prompt có bước kiểm tra ảnh có cây, đếm chuỗi thất bại liên tiếp, băng cảnh báo trên dashboard, sự kiện `camera_alert` |
| 2 | Chấp nhận `binh_thuong` với `do_tin_cay = 0`, và nhận cả trạng thái ngoài enum | `normalize_ai_result()` kiểm enum và ngưỡng `AI_MIN_CONF = 40`; kết quả không đạt bị hạ xuống `khong_xac_dinh` và không được tác động cơ cấu chấp hành |
| 3 | Bơm có thể bật vô thời hạn suốt cửa sổ cooldown một giờ | Cơ chế `pulse()` dùng chung, mọi lệnh ép actuator đều có hạn. Tưới khẩn cấp 60 giây rồi tự trả `AUTO` |
| 4 | Lịch sử cảm biến chỉ nằm trong RAM, mất khi restart | SQLite chế độ WAL, ghi mỗi 60 giây, nạp lại 60 phút gần nhất khi khởi động |
| 5 | Event log chỉ ghi sự kiện AI, không dựng lại được lịch sử lệnh | Bốn bảng `sensor_readings`, `ai_diagnosis`, `commands`, `events`, kèm endpoint xuất CSV |
| 6 | Ảnh bị ghi đè, không truy vết chẩn đoán về khung ảnh sinh ra nó | Tên file có dấu thời gian, giữ 50 file mới nhất, dải ảnh thu nhỏ kèm nhãn chẩn đoán |
| 7 | AI chỉ tác động một trong bốn trạng thái, còn lại chỉ ghi log | Ma trận quyết định AI × độ ẩm đất, ba ô đổi hành vi thật |
| 8 | Chạy tay, log cho thấy sáu lần khởi động rải rác | systemd với `Restart=always` và `RestartSec=10` |
| 9 | Tên cổng đổi giữa `ttyUSB0` và `ttyUSB1` | udev rule tạo tên cố định `/dev/esp32` |

Bốn khiếm khuyết tìm thêm ngày 06/08, khi đọc firmware và `main.py` đối chiếu với
nhau thay vì đọc riêng từng bên:

| # | Vấn đề | Cách sửa |
|---|---|---|
| 10 | `main.py` không gửi heartbeat mà watchdog firmware chờ. Do lệnh trùng bị lọc, một quyết định giữ nguyên không sinh byte nào trên serial, nên khoá ban đêm bị nhả sau khoảng 60 giây và có thể tưới trong tối | Gửi `PING` mỗi 10 giây trong `decision_loop`. Đã kiểm chứng trên phần cứng |
| 11 | Khung sự kiện của ESP32 bị đọc như khung cảm biến, xoá sạch số liệu trên dashboard | Bỏ qua khung không có trường `temp`, ghi sang nhật ký sự kiện |
| 12 | Thuộc tính `hidden` vô tác dụng với phần tử có khai báo `display`, làm bốn băng cảnh báo hiện thường trực | Thêm `[hidden]{display:none!important}` |
| 13 | Ghi chú AI chèn vào trang không escape, và giờ trên thumbnail lệch một ký tự | Escape khi chèn, sửa offset `slice` |

## 11. Việc còn lại trước buổi bảo vệ

- Đặt lại camera và xác nhận nhãn "ĐỦ TIN CẬY" theo mục 6. Đây là việc quan trọng nhất.
- Nạp firmware `firmware/v2/v2.ino` để `MIST_LOCK` và watchdog serial có tác dụng.
- Cho hệ thống chạy liên tục 3–5 ngày để có dữ liệu thật cho biểu đồ báo cáo.
- Quay ba kịch bản kiểm thử: tưới khẩn cấp, Time Guard chặn lệnh tay ban đêm, và
  cấm phun sương sau chẩn đoán đốm nâu.
- Chụp màn hình dashboard lúc đã có dữ liệu đầy đủ cho mục 3.4.
- Chạy các truy vấn ở mục 8 và chép kết quả vào mục 3.5.
- Đo độ chính xác mô hình trên tập ảnh tự gán nhãn, thay cho mục `[ TBD ]` còn lại
  trong báo cáo.
- Thêm xác thực cho `/api/command`. Nếu không kịp thì nêu thẳng ở mục 4.2 Future
  Improvements.
