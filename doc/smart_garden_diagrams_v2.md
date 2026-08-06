# Bộ sơ đồ hệ thống — Smart Home Garden (SIC IoT Capstone) — **BẢN v2**

> **Thay cho `smart_garden_diagrams.md` cũ.** Bản cũ mô tả logic v1 và mâu thuẫn với Final Report ở 3 chỗ:
> mức 1 không rẽ theo độ ẩm đất, mức 4 ghi "không ép actuator" (sai với `dom_nau`), và sequence còn ghi
> bounded-pulse là "đề xuất" trong khi nó đã được cài đặt. Bản này đã sửa cả ba.
>
> **PNG đã xuất sẵn ở [`hinh/`](hinh/)**, scale 3x, nền trắng, dán thẳng vào `.docx`
> được. Chỉ cần xuất lại khi sửa mã nguồn sơ đồ (xem mục cuối tài liệu).

## File PNG và vị trí trong báo cáo

| File trong `hinh/` | Mục Final Report | Caption |
|---|---|---|
| `01-kien-truc-tong-quan.png` | 2.1 | Figure 2.1 — System architecture overview |
| `02-cay-quyet-dinh-5-muc.png` | 2.3 | Figure 2.3 — Five-level priority decision tree |
| `03-luong-xu-ly-du-lieu.png` | 2.2 | Figure 2.2 — Data processing flow |
| `04a-sequence-tuoi-khan-cap.png` | 3.5 | Figure 3.5 — Emergency watering sequence with bounded pulse |
| `04b-sequence-watchdog.png` | 2.3 hoặc 3.5 | Figure — Serial watchdog releasing a forced actuator |
| `05-so-do-trien-khai.png` | 3.2 | Figure 3.2 — Deployment and network topology |
| `06-gantt-wbs.png` | 1.4 | Figure 1.1 — Project schedule |
| `07-so-do-chan-cam.png` | 3.3 | Figure 3.3 — ESP32 pin assignment |

Sơ đồ 2 nên đặt riêng một trang khổ ngang. Sơ đồ 7 rất rộng (tỷ lệ khoảng 4.8:1),
đặt ngang hoặc thu theo chiều rộng trang.

| Sơ đồ | Đưa vào mục Final Report | Đổi so với bản cũ |
|---|---|---|
| 1. Kiến trúc tổng quan | 2.1 IoT Service Model | Thêm lớp validate, SQLite 4 bảng, kho ảnh, cảnh báo camera, **watchdog serial + PING** |
| 2. Cây quyết định 5 mức | 2.3 Service Implementation | **Sửa nặng** — mức 1 rẽ theo độ ẩm đất, mức 4 là ma trận fusion |
| 3. Luồng xử lý dữ liệu | 2.2 Data Processing | Thêm `normalize_ai_result()`, SQLite thay cho file log |
| 4. Sequence tưới khẩn cấp | 3.5 Testing and Improvements | **Sửa** — bounded pulse là hiện trạng; thêm nhịp PING và **nhánh hỏng khi Pi chết** |
| 5. Sơ đồ triển khai | 3.2 Network and Communication | Thêm systemd, udev, cổng cố định |
| 6. Gantt WBS | 1.4 Schedule and Milestones | Thêm Phase 5 (26/07–05/08) |
| 7. Sơ đồ chân cắm | 3.3 Hardware Implementation | **Mới** — dùng tạm nếu chưa kịp vẽ Fritzing |

---

## 1. Kiến trúc tổng quan hệ thống
**→ Mục 2.1 · Caption: *Figure 2.1 — System architecture overview.***

```mermaid
flowchart TB
    subgraph CLOUD["☁️ Tầng đám mây"]
        GEM["Gemini Vision API<br/><i>gemini-3.1-flash-lite</i><br/>Trả JSON: trang_thai · do_tin_cay · ghi_chu"]
    end

    subgraph EDGE["🖥️ Tầng biên — Raspberry Pi 5 · main.py (Python đa luồng)"]
        direction TB
        SR["<b>serial_reader</b> (thread)<br/>Đọc JSON 2s/lần<br/>Tự kết nối lại"]
        AI["<b>ai_vision_worker</b> (thread)<br/>OpenCV chụp mỗi 15 phút<br/>Lưu ảnh có dấu thời gian"]
        VAL["<b>normalize_ai_result()</b><br/>Kiểm enum · ngưỡng conf ≥ 40<br/>· có cây trong khung ảnh?<br/><i>Reply hỏng bị loại tại đây</i>"]
        DL["<b>decision_loop</b> (main thread)<br/>Cây ưu tiên 5 mức<br/>Chu kỳ 2 giây<br/>PING mỗi 10 giây"]
        API["<b>dashboard_worker</b> (thread)<br/>Flask REST · 12 endpoint<br/>:5000 bind 0.0.0.0"]
        DB[("SQLite (WAL)<br/>sensor_readings · ai_diagnosis<br/>commands · events")]
        PH[("photos/<br/>leaf_YYYYmmdd_HHMMSS.jpg<br/>giữ 50 file gần nhất")]
    end

    subgraph MCU["🔌 Tầng thiết bị — ESP32 (điều khiển thời gian thực)"]
        direction TB
        SEN["Cảm biến<br/>DHT11 · quang trở · độ ẩm đất"]
        AUTO["<b>Logic AUTO cục bộ</b><br/>Theo ngưỡng trong firmware<br/><i>Chạy độc lập với Pi</i>"]
        ACT["Cơ cấu chấp hành<br/>Relay bơm tưới · Relay phun sương<br/><i>khoá liên động, active LOW</i>"]
        OLED["OLED SSD1306<br/>2 trang luân phiên 3s"]
        WD["<b>checkSerialWatchdog()</b><br/>Quá 60s không nhận gì từ Pi<br/>→ nhả relay, quay về AUTO<br/><i>báo cờ wd_tripped</i>"]
    end

    CAM["📷 USB Camera"]
    WEB["🌐 Trình duyệt cùng LAN<br/>dashboard.html"]

    CAM -->|"cv2.VideoCapture"| AI
    AI <-->|"HTTPS · upload ảnh / JSON"| GEM
    AI --> PH
    AI --> VAL
    VAL --> DL
    SR -->|"latest_sensor"| DL
    DL -->|"send_command (dedupe)"| SR
    SR <-->|"UART 115200<br/>JSON hai chiều"| SEN
    SR -.->|"PING mỗi 10 giây<br/>bằng chứng Pi còn sống"| WD
    WD -->|"huỷ mọi lệnh do Pi đặt"| AUTO
    SEN --> AUTO --> ACT
    SEN --> OLED
    DL -.->|"ghi 4 bảng"| DB
    VAL -.->|"ai_diagnosis / camera_alert"| DB
    SR -.->|"sensor_readings mỗi 60s"| DB
    WEB <-->|"HTTP polling 3s"| API
    API --> DB
    API --> PH
    API -->|"lệnh tay · lease 600s"| DL

    style CLOUD fill:#FAECE7,stroke:#993C1D
    style EDGE fill:#EEEDFE,stroke:#534AB7
    style MCU fill:#E1F5EE,stroke:#0F6E56
    style VAL fill:#FFF4CE,stroke:#8A6D00
    style WD fill:#FFF4CE,stroke:#8A6D00
```

> Hai nút nền vàng là hai lớp chặn độc lập: `normalize_ai_result()` chặn kết quả AI
> không đáng tin đi vào quyết định, `checkSerialWatchdog()` chặn cơ cấu chấp hành
> kẹt ở trạng thái ép khi Pi chết. Vì `send_command()` lọc lệnh trùng, một quyết
> định giữ nguyên lâu không sinh byte nào trên serial, nên `PING` là thứ duy nhất
> phân biệt "quyết định đang ổn định" với "host đã chết".

---

## 2. Cây quyết định 5 mức ưu tiên — **ĐÃ SỬA**
**→ Mục 2.3 · Caption: *Figure 2.3 — Five-level priority decision tree, re-evaluated every two seconds.***
> Nên xuất riêng một trang A4. Đây là hình ăn điểm nhất của cả báo cáo.

```mermaid
flowchart TD
    START(["decision_loop — mỗi 2 giây"]) --> L1{"<b>MỨC 1 — AI KHẨN CẤP</b><br/>trang_thai = heo_ru<br/>VÀ do_tin_cay ≥ 70%<br/>VÀ ngoài cooldown?"}

    L1 -->|Có| SOIL{"<b>Đối chiếu độ ẩm đất</b><br/>soil < 40% ?"}
    SOIL -->|"Đất KHÔ"| E1["🚨 WATER_ON — xung 60 giây<br/>hết hạn tự trả AUTO<br/>Cooldown 3600s<br/>log: emergency_watering"]
    SOIL -->|"Đất ĐỦ ẨM"| E2["🛑 LOCK_IDLE — giữ 900 giây<br/><b>NGHI THỐI RỄ — không tưới</b><br/>log: rootrot_hold"]

    L1 -->|Không| L2{"<b>MỨC 2 — TIME GUARD</b><br/>Giờ hiện tại 19h–6h?"}
    L2 -->|Có| N["🌙 LOCK_IDLE — khoá ban đêm<br/><i>lệnh tay KHÔNG ghi đè được</i>"]

    L2 -->|Không| L3{"<b>MỨC 3 — MANUAL OVERRIDE</b><br/>now < manual_override_until?"}
    L3 -->|Có| M["✋ Giữ nguyên lệnh tay<br/>Lease 600 giây rồi tự nhả<br/>Nguồn: Web / Terminal"]

    L3 -->|Không| L4{"<b>MỨC 4 — MA TRẬN FUSION</b><br/>Có chẩn đoán hợp lệ<br/>(conf ≥ 40)?"}
    L4 -->|"dom_nau"| F1["🍄 MIST_LOCK — cấm phun sương<br/>tưới gốc vẫn chạy theo ngưỡng<br/><b>ĐỔI HÀNH VI THẬT</b><br/>log: fungus_mist_lock"]
    L4 -->|"vang_la"| F2["🌱 AUTO + cảnh báo thiếu đạm<br/><i>chỉ tư vấn — KHÔNG đổi actuator</i>"]
    L4 -->|"binh_thuong / khong_xac_dinh<br/>hoặc không có chẩn đoán"| L5

    L5["<b>MỨC 5 — MẶC ĐỊNH</b><br/>✅ AUTO<br/>ESP32 tự quyết theo ngưỡng cục bộ"]

    E1 --> SEND
    E2 --> SEND
    N --> SEND
    M --> SEND
    F1 --> SEND
    F2 --> SEND
    L5 --> SEND

    SEND["send_command → ESP32<br/><i>dedupe: trùng lệnh cũ thì bỏ qua</i><br/>ghi bảng commands"] --> START

    style L1 fill:#FCEBEB,stroke:#A32D2D
    style SOIL fill:#FCEBEB,stroke:#A32D2D
    style E1 fill:#FCEBEB,stroke:#A32D2D
    style E2 fill:#FCEBEB,stroke:#A32D2D
    style L2 fill:#E6F1FB,stroke:#185FA5
    style N fill:#E6F1FB,stroke:#185FA5
    style L3 fill:#FAEEDA,stroke:#854F0B
    style L4 fill:#F3EAFB,stroke:#6B2D91
    style F1 fill:#F3EAFB,stroke:#6B2D91
    style F2 fill:#F7F7F7,stroke:#808080
    style L5 fill:#EAF3DE,stroke:#3B6D11
```

**Ghi chú đặt dưới hình trong báo cáo:** `MIST_UNLOCK` được phát khi chẩn đoán `dom_nau` không còn xuất
hiện trong chu kỳ kế tiếp. Mọi lệnh ép actuator đều có thời hạn, nên hệ luôn tự quay về `AUTO`.

---

## 3. Luồng xử lý dữ liệu (Data Processing) — **ĐÃ SỬA**
**→ Mục 2.2 · Caption: *Figure 2.2 — Data processing flow from physical sensors to dashboard.***

```mermaid
flowchart LR
    A["Cảm biến vật lý<br/>DHT11 · LDR · độ ẩm đất"] --> B["<b>ESP32</b><br/>LDR: TB 20 mẫu + làm mượt 0.7/0.3<br/>Soil: đổi ADC → %<br/>Đóng gói JSON"]
    B -->|"UART 115200 · 2s/lần"| C["serial_reader<br/>json.loads() — frame hỏng thì bỏ,<br/>không làm sập tiến trình"]

    C --> D["latest_sensor<br/><i>có khoá</i>"]
    C --> E["sensor_history<br/>deque maxlen 240<br/>lấy mẫu 15s → cửa sổ 60 phút"]
    C --> DB1[("SQLite · sensor_readings<br/>ghi mỗi 60s")]

    F["USB Camera"] --> G["capture_image()<br/>OpenCV → JPEG"]
    G --> PH[("photos/leaf_*.jpg<br/>giữ 50 file")]
    G --> H["Gemini Vision<br/>prompt ép trả JSON<br/>+ hỏi 'có cây trong ảnh không?'"]
    H --> V{"<b>normalize_ai_result()</b><br/>1· parse JSON được?<br/>2· trang_thai trong enum?<br/>3· do_tin_cay ≥ 40?<br/>4· có cây trong khung?"}
    V -->|"Hỏng"| X["❌ Loại bỏ<br/>tăng bộ đếm thất bại<br/>→ camera_alert"]
    V -->|"Hợp lệ"| I["latest_ai_result"]
    I --> DB2[("SQLite · ai_diagnosis")]
    X --> DB2

    D --> J["decision_loop<br/>cây ưu tiên 5 mức"]
    I --> J
    J --> K["Lệnh: WATER_ON · MIST_LOCK<br/>AUTO · LOCK_IDLE"]
    K --> B
    J --> DB3[("SQLite · commands + events")]

    D --> L["/api/status"]
    E --> M["/api/history"]
    I --> L
    DB3 --> EV["/api/events + xuất CSV"]
    PH --> PHA["/api/photos"]
    L --> N["Dashboard: gauge · pill<br/>+ <b>lý do của trạng thái hiện tại</b>"]
    M --> O["4 biểu đồ sparkline SVG<br/>tự vẽ path"]

    style H fill:#FAECE7,stroke:#993C1D
    style V fill:#FFF4CE,stroke:#8A6D00
    style X fill:#FCEBEB,stroke:#A32D2D
    style J fill:#EEEDFE,stroke:#534AB7
```

---

## 4. Sequence — kịch bản tưới khẩn cấp — **ĐÃ SỬA**
**→ Mục 3.5 · Caption: *Figure 3.5 — Emergency watering sequence with bounded pulse.***

```mermaid
sequenceDiagram
    autonumber
    participant CAM as USB Camera
    participant AIW as ai_vision_worker
    participant GEM as Gemini Vision
    participant VAL as normalize_ai_result
    participant DL as decision_loop
    participant ESP as ESP32
    participant PUMP as Bơm tưới
    participant DB as SQLite

    Note over AIW: Chu kỳ tự động 15 phút
    AIW->>CAM: capture_image()
    CAM-->>AIW: leaf_20260801_143000.jpg
    AIW->>DB: lưu ảnh vào photos/
    AIW->>GEM: upload ảnh + prompt ép JSON
    GEM-->>VAL: {"trang_thai":"heo_ru","do_tin_cay":95,"co_cay":true}
    VAL->>VAL: enum ✓ · conf 95 ≥ 40 ✓ · có cây ✓
    VAL->>DB: ai_diagnosis
    VAL->>DL: latest_ai_result

    DL->>DL: MỨC 1 — 95% ≥ 70% ✓ và ngoài cooldown ✓
    DL->>DL: đối chiếu soil = 28% < 40% → ĐẤT KHÔ
    DL->>DB: events: emergency_watering
    DL->>ESP: WATER_ON
    ESP->>PUMP: đóng relay (active LOW)
    ESP-->>DL: {water:true, mode:"MANUAL", reason:"host cmd"}

    Note over DL,ESP: Bounded pulse — hẹn giờ 60 giây (EMERGENCY_WATER_DURATION).<br/>send_command lọc lệnh trùng nên WATER_ON không được phát lại.<br/>PING là byte duy nhất chạy trên serial trong lúc này.
    loop mỗi 10 giây trong suốt thời gian giữ lệnh
        DL->>ESP: PING
        ESP->>ESP: g_lastSerialMs = millis()
    end

    DL->>DL: hết 60s → hết hạn xung
    DL->>ESP: AUTO
    ESP->>PUMP: mở relay
    ESP-->>DL: {water:false, mode:"AUTO"}
    DL->>DB: events: pulse_released

    Note over DL: Khoá cooldown 3600 giây —<br/>cùng triệu chứng không kích hoạt lại
```

Nhánh hỏng — Pi mất điện hoặc treo ngay sau khi phát `WATER_ON`:

```mermaid
sequenceDiagram
    autonumber
    participant DL as decision_loop (Pi)
    participant ESP as ESP32
    participant PUMP as Bơm tưới

    DL->>ESP: WATER_ON
    ESP->>PUMP: đóng relay
    ESP->>ESP: g_manualFromSerial = true

    Note over DL: Pi mất điện / crash / systemctl stop
    DL--xESP: PING ngừng phát

    Note over ESP: Đếm từ g_lastSerialMs
    ESP->>ESP: millis() - g_lastSerialMs > 60000<br/>checkSerialWatchdog()
    ESP->>PUMP: nhả relay
    ESP->>ESP: manualMode = false · g_mistLocked = false<br/>g_watchdogTripped = true
    ESP--)DL: {"event":"watchdog"} · wd_tripped = true

    Note over ESP: Quay về logic AUTO cục bộ.<br/>Không có lớp này, bơm chạy đến khi hết nước.
```

---

## 5. Sơ đồ triển khai (Deployment)
**→ Mục 3.2 · Caption: *Figure 3.2 — Deployment and network topology.***

```mermaid
flowchart LR
    subgraph LAN["Mạng LAN nội bộ (tin cậy)"]
        subgraph PIBOX["Raspberry Pi 5"]
            SVC["systemd: smart-garden.service<br/>Restart=always · RestartSec=10"]
            APP["main.py<br/>Flask bind 0.0.0.0:5000"]
            UDEV["udev rule → /dev/esp32<br/>CP2102 10c4:ea60<br/>CH340 1a86:7523"]
            SQL[("SQLite WAL + photos/")]
        end
        PC["Laptop / Điện thoại<br/>Trình duyệt · polling 3s"]
    end

    subgraph WIRED["Kết nối có dây"]
        ESP["ESP32 DevKit<br/>web server riêng :80<br/>tự làm mới 5s"]
        USB["USB Camera<br/>/dev/video0"]
    end

    NET(("Internet"))
    GEM["Gemini API<br/>generativelanguage.googleapis.com"]

    SVC --> APP
    APP --> SQL
    APP --> UDEV
    UDEV ---|"USB Serial · 115200 baud"| ESP
    USB --- APP
    PC -->|"HTTP :5000<br/><b>⚠ chưa có xác thực</b>"| APP
    PC -.->|"HTTP :80 (xem dự phòng)"| ESP
    APP -->|"HTTPS 443"| NET
    NET --> GEM

    style GEM fill:#FAECE7,stroke:#993C1D
    style PIBOX fill:#EEEDFE,stroke:#534AB7
    style ESP fill:#E1F5EE,stroke:#0F6E56
```

---

## 6. Gantt — WBS cho báo cáo
**→ Mục 1.4 · Caption: *Figure 1.1 — Project schedule (Gantt view of the Work Breakdown Structure).***
> Đã đồng bộ với file WBS Excel (có Phase 5). Sửa `done`/`active` cho khớp thực tế trước khi nộp.

```mermaid
gantt
    title Smart Home Garden — Capstone Project Schedule
    dateFormat YYYY-MM-DD
    axisFormat %d/%m

    section 1. Hardware & Firmware
    Sensor integration (DHT11/LDR/Soil)   :done, a1, 2026-07-06, 2d
    Actuator & relay control              :done, a2, 2026-07-07, 2d
    OLED & WiFiManager portal             :done, a3, 2026-07-08, 3d

    section 2. Serial & Time Guard
    Bidirectional serial protocol         :done, b1, 2026-07-10, 3d
    Time Guard night lockout 19h-6h       :done, b2, 2026-07-12, 2d

    section 3. AI Vision
    Camera capture module (OpenCV)        :done, c1, 2026-07-13, 2d
    Gemini API & prompt engineering       :done, c2, 2026-07-14, 4d
    Accuracy evaluation (self-labeled)    :active, c3, 2026-07-17, 3d

    section 4. Integration & Deployment
    Merge serial + Time Guard + AI        :done, d1, 2026-07-19, 3d
    systemd service setup                 :done, d2, 2026-07-21, 2d
    End-to-end demo testing               :done, d3, 2026-07-22, 3d
    Final Report & slides                 :active, d4, 2026-07-23, 3d

    section 5. Hardening & Fusion (v2)
    Camera blind-spot detection           :done, e1, 2026-07-26, 2d
    AI confidence validation layer        :done, e2, 2026-07-27, 2d
    Bounded-pulse actuator safety         :done, e3, 2026-07-28, 2d
    SQLite persistence + photo archive    :done, e4, 2026-07-29, 2d
    AI x soil-moisture decision matrix    :done, e5, 2026-07-30, 2d
    systemd + udev fixed port             :done, e6, 2026-08-01, 1d
    Field test 3-5 days (real plant)      :active, e7, 2026-08-01, 5d
    Demo video - 3 scenarios              :active, e8, 2026-08-03, 3d
```

---

## 7. Sơ đồ chân cắm — **MỚI**
**→ Mục 3.3 · Caption: *Figure 3.3 — ESP32 pin assignment.***
> Đây là bản **dùng tạm**. Nếu kịp thời gian, hãy vẽ lại bằng **Fritzing** (có sẵn ESP32, module relay,
> DHT11) hoặc **draw.io** thư viện Electrical — sơ đồ có hình linh kiện thật sẽ ăn điểm hơn ở tiêu chí
> *Proper tool usage*.

```mermaid
flowchart LR
    subgraph IN["Đầu vào"]
        D["DHT11<br/>nhiệt độ + độ ẩm KK"]
        L["Quang trở LDR<br/>+ điện trở kéo"]
        S["Đầu dò độ ẩm đất<br/>loại điện trở"]
        BTN["Nút BOOT<br/>giữ 3s = xoá WiFi"]
    end

    subgraph ESP["ESP32 DevKit"]
        direction TB
        P4["GPIO4 — 1-Wire"]
        P34["GPIO34 — ADC1, input-only"]
        P35["GPIO35 — ADC1, input-only"]
        P0["GPIO0 — BOOT"]
        P26["GPIO26 — digital out"]
        P27["GPIO27 — digital out"]
        P21["GPIO21 — I2C SDA"]
        P22["GPIO22 — I2C SCL"]
    end

    subgraph OUT["Đầu ra"]
        R1["Relay 1 — bơm tưới gốc<br/><b>active LOW</b>"]
        R2["Relay 2 — phun sương<br/><b>active LOW</b>"]
        OL["OLED SSD1306<br/>128x64, I2C 0x3C"]
    end

    D --> P4
    L --> P34
    S --> P35
    BTN --> P0
    P26 --> R1
    P27 --> R2
    P21 --> OL
    P22 --> OL

    style ESP fill:#E1F5EE,stroke:#0F6E56
    style IN fill:#EEEDFE,stroke:#534AB7
    style OUT fill:#FAECE7,stroke:#993C1D
```

**Hai chú thích kỹ thuật nên viết kèm hình** (giám khảo hay hỏi):
1. Hai kênh analog dùng **GPIO34 và GPIO35 thuộc ADC1** vì ADC2 bị vô hiệu khi WiFi đang bật — đây là
   ràng buộc phần cứng của ESP32, không phải lựa chọn ngẫu nhiên.
2. Module relay **active LOW**: mức HIGH khi khởi động là trạng thái *nhả*, nên bơm không bị đóng nhầm
   trong lúc ESP32 đang boot.

---

## Xuất lại PNG sau khi sửa sơ đồ

Các file trong `hinh/` được dựng bằng Chrome headless, không cần cài mermaid-cli.
Script đo kích thước SVG trước rồi chụp đúng khung ở `--force-device-scale-factor=3`,
nên ảnh không thừa lề và không bị cắt:

```bash
python doc/mkpng.py doc/smart_garden_diagrams_v2.md /tmp/render doc/hinh
```

Sửa mã sơ đồ xong thì chạy lại lệnh trên, mọi PNG được ghi đè.

Hai lỗi đã gặp khi dựng, ghi lại để khỏi mất công lần sau:

- Dấu chấm phẩy trong `Note` của `sequenceDiagram` bị hiểu là dấu kết thúc câu lệnh
  và làm hỏng cả khối. Dùng dấu chấm thay thế.
- Hai cạnh cùng đổ vào một nút sẽ bị dagre đặt nhãn chồng lên nhau. Bỏ nhãn của một
  trong hai cạnh, rút ngắn chữ không giải quyết được.

## Ghi chú khi xuất ảnh dán vào .docx

1. **mermaid.live** → tab *Actions* → PNG, đổi `scale` thành **3**. Mặc định 1x sẽ mờ khi in A4.
2. Nếu Word làm vỡ ảnh: xuất **SVG** rồi Insert → Picture — Word giữ nguyên vector, phóng to không mờ.
3. Sơ đồ 2 nên để **riêng một trang ngang** nếu chữ bị nhỏ.
4. Caption chuẩn học thuật đặt **dưới** hình, in nghiêng, đánh số theo mục: *Figure 2.3 — ...*
5. Trong Final Report đã có sẵn 8 khung nét đứt đúng vị trí — chỉ cần thay khung bằng ảnh.
