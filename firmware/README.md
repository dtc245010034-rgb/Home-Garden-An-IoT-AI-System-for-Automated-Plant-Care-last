# Firmware ESP32

Mỗi phiên bản nằm trong **thư mục riêng**, tên file `.ino` trùng tên thư mục —
đây là yêu cầu bắt buộc của Arduino IDE để mở được sketch. Trước đây hai file
`.ino` nằm chung một thư mục nên IDE cố biên dịch cả hai và báo lỗi trùng hàm.

| Thư mục | Nạp? | Nội dung |
|---|---|---|
| [`v2/`](v2/v2.ino) | ✅ **Nạp bản này** | v2.1 — có `MIST_LOCK`/`MIST_UNLOCK` và watchdog serial |
| [`v1/`](v1/v1.ino) | ❌ Không | Bản gốc, giữ lại để đối chiếu trong báo cáo |

## Nạp v2

1. Arduino IDE → **Tools → Board** → cài package *esp32 by Espressif Systems*.
2. **Sketch → Include Library → Manage Libraries**, cài:
   `WiFiManager` · `Adafruit GFX Library` · `Adafruit SSD1306` · `DHT sensor library`.
3. Mở `firmware/v2/v2.ino` → chọn board *ESP32 Dev Module* → chọn cổng COM → **Upload**.

> ⚠️ Nếu Raspberry Pi đang chạy service, nó giữ cổng serial và IDE sẽ báo
> *port busy*. Dừng trước khi nạp:
> ```bash
> sudo systemctl stop smart-garden
> ```

## Khác biệt v1 → v2.1

| | v1 | v2.1 |
|---|---|---|
| `MIST_LOCK` / `MIST_UNLOCK` | ❌ | ✅ Khoá riêng phun sương, **vẫn giữ AUTO** cho tưới gốc |
| Watchdog serial | ❌ | ✅ Pi im lặng > 60 giây → tự huỷ chế độ thủ công, quay về `AUTO` |
| Trường `mist_locked`, `wd_tripped` trong JSON | ❌ | ✅ |
| `decideMode()` xử lý trường hợp khoá sương | ❌ | ✅ Khô + nóng mà bị khoá sương → tưới gốc thay vì phun sương |

v1 vẫn chạy được với `main.py` (lệnh lạ bị bỏ qua an toàn), nhưng mất ma trận
fusion đầy đủ và **mất luôn lớp an toàn watchdog**.

## Cấu hình WiFi

Firmware dùng **WiFiManager** — không hard-code SSID/mật khẩu:

1. Nạp firmware, cấp nguồn ESP32.
2. Điện thoại kết nối WiFi `SmartGarden-Setup`, mật khẩu `12345678`.
3. Portal tự mở → chọn WiFi nhà và nhập mật khẩu.
4. Xoá cấu hình cũ: **giữ nút BOOT (GPIO 0) khi cấp nguồn**.
