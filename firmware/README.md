# Firmware ESP32

Bản đang dùng: [`v2/v2.ino`](v2/v2.ino) — firmware v2.1, có `MIST_LOCK`/`MIST_UNLOCK`
và watchdog serial. Tên file `.ino` trùng tên thư mục vì Arduino IDE bắt buộc
như vậy mới mở được sketch.

Bản v1 đã xoá khỏi repo. Cần đối chiếu thì lấy từ lịch sử git:

```bash
git show e02db11:firmware/v1/v1.ino > /tmp/v1.ino
```

## Nạp firmware

1. Arduino IDE → **Tools → Board** → cài package *esp32 by Espressif Systems*.
2. **Sketch → Include Library → Manage Libraries**, cài:
   `WiFiManager` · `Adafruit GFX Library` · `Adafruit SSD1306` · `DHT sensor library`.
3. Mở `firmware/v2/v2.ino` → chọn board *ESP32 Dev Module* → chọn cổng COM → **Upload**.

> ⚠️ Nếu Raspberry Pi đang chạy service, nó giữ cổng serial và IDE sẽ báo
> *port busy*. Dừng trước khi nạp:
> ```bash
> sudo systemctl stop smart-garden
> ```

## Watchdog serial — vì sao cần `PING`

Firmware ghi lại thời điểm nhận dòng cuối cùng từ Pi. Quá 60 giây không nhận được
gì **và** chế độ thủ công hiện tại do Pi đặt ra, ESP32 tự nhả hai relay, quay về
`AUTO` và bật cờ `wd_tripped`. Chế độ thủ công người dùng bấm trên web UI của
chính ESP32 thì không bị đụng tới.

Vì `send_command()` trong `main.py` lọc lệnh trùng, một quyết định giữ nguyên lâu
(khoá ban đêm, khoá thối rễ, override tay) **không sinh byte nào** trên serial.
Nếu không có gì bù, watchdog sẽ hiểu là Pi đã chết và huỷ đúng những trạng thái
cần giữ nhất. Vì vậy `decision_loop` gửi `PING` mỗi 10 giây — lệnh này không đổi
trạng thái gì, chỉ để phân biệt "quyết định đang ổn định" với "host đã chết".

## Khác biệt so với v1

| | v1 | v2.1 |
|---|---|---|
| `MIST_LOCK` / `MIST_UNLOCK` | ❌ | ✅ Khoá riêng phun sương, **vẫn giữ AUTO** cho tưới gốc |
| Watchdog serial | ❌ | ✅ |
| Trường `mist_locked`, `wd_tripped` trong JSON | ❌ | ✅ |
| `decideMode()` xử lý trường hợp khoá sương | ❌ | ✅ Khô + nóng mà bị khoá sương → tưới gốc thay vì phun sương |

## Cấu hình WiFi

Firmware dùng **WiFiManager** — không hard-code SSID/mật khẩu:

1. Nạp firmware, cấp nguồn ESP32.
2. Điện thoại kết nối WiFi `SmartGarden-Setup`, mật khẩu `12345678`.
3. Portal tự mở → chọn WiFi nhà và nhập mật khẩu.
4. Xoá cấu hình cũ: **giữ nút BOOT (GPIO 0) khi cấp nguồn**.
