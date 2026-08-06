#!/usr/bin/env python3
"""
Smart Home Garden — SIC IoT Capstone
main.py v2 — Serial 2 chiều (ESP32) + Time Guard + Gemini Vision + Ma trận fusion
              + Lưu trữ SQLite bền vững + Kho ảnh + Web Dashboard (LAN)

=============================================================================
THỨ TỰ ƯU TIÊN QUYẾT ĐỊNH — đánh giá lại mỗi vòng lặp (2 giây).
Không mức nào (trừ mức 3) có thể bị mức thấp hơn âm thầm ghi đè.
=============================================================================

  MỨC 1 — AI KHẨN CẤP
      AI báo "heo_ru" với độ tin cậy >= AI_EMERGENCY_CONF.
      Hành động phụ thuộc độ ẩm đất (SENSOR FUSION):
        • Đất khô (hoặc mất số liệu đất) -> tưới XUNG WATER_ON trong
          EMERGENCY_WATER_DURATION giây rồi TỰ TRẢ VỀ AUTO.
        • Đất còn đủ ẩm -> KHÔNG tưới. Nghi thối rễ / sốc nhiệt.
          Khoá LOCK_IDLE trong ROOTROT_HOLD_DURATION giây + báo động đỏ.
      Luôn được kiểm tra trước tiên, kể cả khi đang override thủ công.

  MỨC 2 — TIME GUARD
      19h-6h -> LOCK_IDLE. Luôn kiểm tra trước override thủ công
      (an toàn ban đêm không thể bị lệnh tay ghi đè).

  MỨC 3 — MANUAL OVERRIDE
      Lệnh thủ công (terminal hoặc Web Dashboard) có hiệu lực
      MANUAL_OVERRIDE_DURATION giây — CHỈ khi không khẩn cấp và không ban đêm.

  MỨC 4 — MA TRẬN FUSION (AI x ĐỘ ẨM ĐẤT)
      Chỉ áp dụng khi kết quả AI ĐÁNG TIN (đúng enum VÀ do_tin_cay >= AI_MIN_CONF).
      Đây là phần AI thực sự thay đổi hành vi cơ cấu chấp hành, không chỉ cảnh báo:
        • dom_nau            -> MIST_LOCK: cấm phun sương (nấm gặp ẩm sẽ lan),
                                vẫn cho phép tưới gốc theo ngưỡng của ESP32.
        • heo_ru (tin cậy thấp) + đất ẩm -> cảnh báo theo dõi, giữ AUTO.
        • vang_la + đất ẩm   -> cảnh báo thiếu dinh dưỡng (không phải thiếu nước).
        • vang_la + đất khô  -> AUTO, để ESP32 tưới theo ngưỡng.
        • binh_thuong        -> MIST_UNLOCK + AUTO.

  MỨC 5 — MẶC ĐỊNH
      Không có gì bất thường -> AUTO, ESP32 tự quyết theo cảm biến.

=============================================================================
LỆNH GỬI XUỐNG ESP32
=============================================================================
  WATER_ON / WATER_OFF / MIST_ON / MIST_OFF / AUTO / LOCK_IDLE  (firmware gốc)
  MIST_LOCK / MIST_UNLOCK                                        (firmware v2)

  Firmware CŨ chưa có MIST_LOCK sẽ bỏ qua lệnh lạ một cách an toàn
  (readSerialCommand không khớp chuỗi nào thì không làm gì), nên main.py này
  chạy được với cả firmware cũ lẫn mới. Muốn ma trận fusion hoạt động đầy đủ
  (và có lớp an toàn watchdog) thì nạp firmware/v2/v2.ino.

=============================================================================
LƯU TRỮ
=============================================================================
  smart_garden.db          SQLite (WAL) — sensor_readings, ai_diagnosis,
                           events, commands. KHÔNG mất khi khởi động lại.
  photos/leaf_*.jpg        Kho ảnh, giữ PHOTO_KEEP file gần nhất.
  smart_garden_events.log  Giữ nguyên JSON-lines để tương thích ngược.
"""

import os
import re
import sys
import csv
import json
import time
import glob
import socket
import sqlite3
import logging
import threading
from collections import deque
from datetime import datetime

import cv2
import serial
from google import genai
from flask import Flask, jsonify, request, send_file, Response

# ============================ CẤU HÌNH ============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Serial ---
PORT = os.environ.get('SG_SERIAL_PORT', '/dev/ttyUSB0')
BAUD = 115200

# --- Camera & AI ---
MODEL_NAME = os.environ.get('SG_MODEL', 'gemini-3.1-flash-lite')
CAM_INDEX = int(os.environ.get('SG_CAM_INDEX', '0'))
CAM_WARMUP_FRAMES = 6          # bỏ vài khung đầu — khung đầu của webcam thường tối/mờ
CAM_WIDTH, CAM_HEIGHT = 1280, 720

AI_CHECK_INTERVAL = 15 * 60    # 15 phút / lần chụp + chẩn đoán định kỳ
AI_MIN_CONF = 40               # dưới ngưỡng này -> coi là "khong_xac_dinh" (BLOCKER 2)
AI_EMERGENCY_CONF = 70         # ngưỡng coi là khẩn cấp
AI_EMERGENCY_COOLDOWN = 60 * 60
CHECK_LEAF_COOLDOWN = 60       # chống spam quota Gemini
CAMERA_BLIND_THRESHOLD = 3     # N lần liên tiếp không nhận diện được -> cảnh báo camera (BLOCKER 1)

# --- Thời lượng cơ cấu chấp hành (BLOCKER 3) ---
EMERGENCY_WATER_DURATION = 60   # giây — tưới khẩn cấp rồi TỰ TRẢ AUTO
ROOTROT_HOLD_DURATION = 15 * 60 # giây — khoá tưới khi nghi thối rễ
ROOTROT_COOLDOWN = 30 * 60

# --- Ngưỡng fusion (đồng bộ với SOIL_DRY_PCT_THRESHOLD trong firmware) ---
SOIL_DRY_THRESHOLD = 40
SENSOR_STALE_SEC = 15          # quá số giây này coi như mất số liệu ESP32

# --- Vòng lặp ---
DECISION_LOOP_INTERVAL = 2
MANUAL_OVERRIDE_DURATION = 10 * 60

# --- Nhịp tim serial ---
# Firmware v2.1 có watchdog: im lặng quá SERIAL_WATCHDOG_MS (60s) thì ESP32 tự
# huỷ chế độ thủ công do Pi đặt và quay về AUTO. Vì send_command() lọc lệnh trùng,
# một quyết định giữ nguyên lâu (LOCK_IDLE ban đêm, khoá thối rễ, override tay)
# sẽ không sinh thêm byte nào -> watchdog nổ oan. PING nuôi watchdog mà không
# làm đổi trạng thái ESP32.
PING_INTERVAL = 10

# --- Lịch sử & lưu trữ ---
HISTORY_SAMPLE_INTERVAL = 15   # giây giữa 2 điểm trong RAM (biểu đồ realtime)
HISTORY_MAXLEN = 240           # 240 x 15s ≈ 60 phút trong RAM
DB_SENSOR_INTERVAL = 60        # giây giữa 2 lần ghi cảm biến xuống SQLite
DB_PATH = os.path.join(BASE_DIR, 'smart_garden.db')
PHOTO_DIR = os.path.join(BASE_DIR, 'photos')
PHOTO_KEEP = 50
LATEST_IMG = os.path.join(PHOTO_DIR, 'latest.jpg')
EVENTS_LOG_PATH = os.path.join(BASE_DIR, 'smart_garden_events.log')

# --- Time Guard ---
NIGHT_START_HOUR = 19
NIGHT_END_HOUR = 6

# --- Dashboard ---
DASHBOARD_HOST = '0.0.0.0'
DASHBOARD_PORT = int(os.environ.get('SG_PORT', '5000'))

VALID_COMMANDS = {"WATER_ON", "WATER_OFF", "MIST_ON", "MIST_OFF",
                  "AUTO", "LOCK_IDLE", "MIST_LOCK", "MIST_UNLOCK"}
MANUAL_COMMANDS = {"WATER_ON", "WATER_OFF", "MIST_ON", "MIST_OFF", "AUTO", "LOCK_IDLE"}
VALID_AI_STATES = {"binh_thuong", "vang_la", "dom_nau", "heo_ru"}

# ======================= MÀU ANSI TERMINAL ========================
C_GREEN, C_RED, C_YELLOW = '\033[92m', '\033[91m', '\033[93m'
C_CYAN, C_BLUE, C_BOLD, C_RESET = '\033[96m', '\033[94m', '\033[1m', '\033[0m'

AI_EMOJI = {
    "binh_thuong": "🟢", "vang_la": "🟡", "dom_nau": "🟠",
    "heo_ru": "🔴", "khong_xac_dinh": "⚪",
}

# ========================= STATE DÙNG CHUNG =========================
state_lock = threading.Lock()
events_log_lock = threading.Lock()
db_lock = threading.Lock()

latest_sensor = {}
latest_ai_result = None
last_sensor_time = 0.0
last_sent_cmd = None
last_sent_reason = ""
last_decision_level = "—"
manual_override_until = 0.0
last_leaf_check_time = 0.0
mist_locked = False
camera_blind_streak = 0
camera_alert = None            # str hoặc None
last_photo_name = None

sensor_history = deque(maxlen=HISTORY_MAXLEN)
last_history_sample_time = 0.0
last_db_sensor_time = 0.0
last_ping_time = 0.0

# Bộ đếm xung dùng chung cho mọi hành động có thời hạn (BLOCKER 3)
# name -> {"until": epoch hết hiệu lực, "cool": epoch hết cooldown}
pulse_state = {}

# ==================== KIỂM TRA API KEY TRƯỚC ====================
if "GEMINI_API_KEY" not in os.environ:
    print("Thiếu biến môi trường GEMINI_API_KEY. "
          "Hãy export GEMINI_API_KEY=... (hoặc dùng EnvironmentFile với systemd) trước khi chạy.")
    sys.exit(1)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


# ========================= LỚP LƯU TRỮ SQLITE =========================
def db_connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


_db = db_connect()


def db_init():
    """Tạo bảng nếu chưa có. WAL cho phép đọc (dashboard) song song với ghi."""
    with db_lock:
        _db.execute("PRAGMA journal_mode=WAL")
        _db.execute("PRAGMA synchronous=NORMAL")
        _db.executescript("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            ts     TEXT NOT NULL,
            epoch  REAL NOT NULL,
            temp   REAL, humi REAL, soil INTEGER, light INTEGER,
            water  INTEGER, mist INTEGER, mode TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sensor_epoch ON sensor_readings(epoch);

        CREATE TABLE IF NOT EXISTS ai_diagnosis (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         TEXT NOT NULL,
            epoch      REAL NOT NULL,
            source     TEXT,
            trang_thai TEXT,
            raw_state  TEXT,
            do_tin_cay INTEGER,
            trusted    INTEGER,
            ghi_chu    TEXT,
            photo      TEXT,
            soil       INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_ai_epoch ON ai_diagnosis(epoch);

        CREATE TABLE IF NOT EXISTS commands (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            ts     TEXT NOT NULL,
            epoch  REAL NOT NULL,
            cmd    TEXT, level TEXT, reason TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_cmd_epoch ON commands(epoch);

        CREATE TABLE IF NOT EXISTS events (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            ts     TEXT NOT NULL,
            epoch  REAL NOT NULL,
            event  TEXT, detail TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_event_epoch ON events(epoch);
        """)
        _db.commit()


def db_exec(sql, params=()):
    try:
        with db_lock:
            _db.execute(sql, params)
            _db.commit()
    except Exception as e:
        print(f"{C_RED}⚠️  Lỗi ghi SQLite: {e}{C_RESET}")


def db_query(sql, params=()):
    try:
        with db_lock:
            return [dict(r) for r in _db.execute(sql, params).fetchall()]
    except Exception as e:
        print(f"{C_RED}⚠️  Lỗi đọc SQLite: {e}{C_RESET}")
        return []


def log_event(event_type, data=None):
    """Ghi song song 2 nơi: SQLite (truy vấn được) và JSON-lines (tương thích ngược)."""
    now = time.time()
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    detail = json.dumps(data or {}, ensure_ascii=False)
    db_exec("INSERT INTO events(ts,epoch,event,detail) VALUES(?,?,?,?)",
            (ts, now, event_type, detail))
    entry = {"ts": ts, "event": event_type}
    if data:
        entry.update(data)
    try:
        with events_log_lock:
            with open(EVENTS_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"{C_RED}⚠️  Không ghi được event log: {e}{C_RESET}")


def db_restore_history():
    """Nạp lại 60 phút cảm biến gần nhất vào RAM sau khi khởi động lại.
    Đây là điểm khác biệt lớn nhất so với v1: biểu đồ không còn trống trơn
    mỗi lần service restart."""
    cutoff = time.time() - HISTORY_MAXLEN * HISTORY_SAMPLE_INTERVAL
    rows = db_query(
        "SELECT ts,temp,humi,soil,light FROM sensor_readings "
        "WHERE epoch >= ? ORDER BY epoch ASC LIMIT ?", (cutoff, HISTORY_MAXLEN))
    for r in rows:
        sensor_history.append({
            "t": r["ts"][11:19],
            "temp": r["temp"], "humi": r["humi"],
            "soil": r["soil"], "light": r["light"],
        })
    if rows:
        print(f"{C_GREEN}✅ Khôi phục {len(rows)} điểm lịch sử cảm biến từ SQLite{C_RESET}")


# ==================== QUẢN LÝ SERIAL (TỰ RECONNECT) ====================
class SerialManager:
    """Bọc pyserial để tự kết nối lại khi mất kết nối, dùng chung an toàn
    giữa nhiều thread (đọc, ghi, dashboard, vòng lặp quyết định)."""

    def __init__(self):
        self.write_lock = threading.Lock()
        self.ser = self._connect()

    def _connect(self):
        warned = False
        while True:
            try:
                s = serial.Serial(PORT, BAUD, timeout=2)
                time.sleep(2)  # chờ ESP32 reset sau khi mở cổng
                return s
            except serial.SerialException:
                if not warned:
                    print(f"{C_RED}Không tìm thấy {PORT}, đang thử lại mỗi 2s...{C_RESET}")
                    warned = True
                time.sleep(2)

    def reconnect(self):
        print(f"\n{C_RED}{C_BOLD}⚠️  Mất kết nối với ESP32! Đang kết nối lại...{C_RESET}")
        log_event("error", {"where": "serial", "message": "Mất kết nối ESP32, đang kết nối lại"})
        self.ser = self._connect()
        print(f"{C_GREEN}✅ Đã khôi phục kết nối!{C_RESET}\n")

    def write(self, data: bytes):
        with self.write_lock:
            try:
                self.ser.write(data)
            except serial.SerialException:
                self.reconnect()

    def readline(self) -> bytes:
        try:
            return self.ser.readline()
        except serial.SerialException:
            self.reconnect()
            return b''


# ========================= TIME GUARD =========================
def is_nighttime():
    h = datetime.now().hour
    return h >= NIGHT_START_HOUR or h < NIGHT_END_HOUR


# ==================== BỘ ĐẾM XUNG (chống chạy vô hạn) ====================
def pulse(name, duration, cooldown):
    """Quản lý một hành động có thời hạn.
    Trả về True nếu hành động ĐANG hiệu lực, False nếu đã hết / đang cooldown.

    Đây là lời giải cho BLOCKER 3: mọi lệnh ép actuator đều phải đi qua đây
    nên KHÔNG BAO GIỜ có chuyện bơm bật vô thời hạn."""
    now = time.time()
    p = pulse_state.setdefault(name, {"until": 0.0, "cool": 0.0})
    if now < p["until"]:
        return True
    if now < p["cool"]:
        return False
    p["until"] = now + duration
    p["cool"] = now + duration + cooldown
    return True


def pulse_remaining(name):
    p = pulse_state.get(name)
    if not p:
        return 0
    return max(0, int(p["until"] - time.time()))


# ========================= CAMERA & KHO ẢNH =========================
def prune_photos():
    """Giữ PHOTO_KEEP ảnh mới nhất, xoá phần còn lại — tránh đầy thẻ nhớ."""
    files = sorted(glob.glob(os.path.join(PHOTO_DIR, 'leaf_*.jpg')))
    for f in files[:-PHOTO_KEEP]:
        try:
            os.remove(f)
        except OSError:
            pass


def capture_image():
    """Chụp ảnh, lưu vào kho photos/leaf_YYYYmmdd_HHMMSS.jpg và cập nhật latest.jpg.
    Bỏ vài khung hình đầu vì webcam USB thường trả khung đầu tối hoặc mờ."""
    global last_photo_name
    os.makedirs(PHOTO_DIR, exist_ok=True)

    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Không mở được camera index {CAM_INDEX} — kiểm tra `ls /dev/video*`")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    frame = None
    for _ in range(CAM_WARMUP_FRAMES):
        ret, f = cap.read()
        if ret:
            frame = f
        time.sleep(0.05)
    cap.release()

    if frame is None:
        raise RuntimeError("Không đọc được khung hình — kiểm tra kết nối camera")

    name = datetime.now().strftime('leaf_%Y%m%d_%H%M%S.jpg')
    path = os.path.join(PHOTO_DIR, name)
    if not cv2.imwrite(path, frame):
        raise RuntimeError(f"Ghi file thất bại tại {path} — kiểm tra quyền thư mục")

    cv2.imwrite(LATEST_IMG, frame)
    prune_photos()
    with state_lock:
        last_photo_name = name
    return path, name


# ========================= GEMINI VISION =========================
PROMPT = """Bạn đang xem ảnh chụp từ camera giám sát một khay rau cải ngọt/cải thìa.

BƯỚC 1 — Kiểm tra ảnh có thực sự chứa lá cây rau không.
Nếu ảnh KHÔNG chứa cây (ví dụ chỉ có bàn, tường, người, máy tính, phòng học),
bắt buộc trả trang_thai = "khong_xac_dinh" và do_tin_cay = 0.

BƯỚC 2 — Nếu có cây, phân loại tình trạng lá.

Trả lời CHỈ bằng JSON, không thêm chữ nào khác, không dùng markdown:
{"trang_thai": "binh_thuong" hoặc "vang_la" hoặc "dom_nau" hoặc "heo_ru" hoặc "khong_xac_dinh",
 "do_tin_cay": số nguyên 0-100,
 "ghi_chu": "mô tả ngắn gọn bằng tiếng Việt, tối đa 25 từ"}"""


def normalize_ai_result(raw, soil=None):
    """BLOCKER 2 — chuẩn hoá và kiểm chứng kết quả AI.

    Model có thể trả trạng thái ngoài enum (thực tế đã xảy ra: "khong_xac_dinh")
    hoặc trả "binh_thuong" với do_tin_cay = 0 (khi camera chĩa nhầm chỗ).
    v1 chấp nhận cả hai -> false negative nguy hiểm. v2 chặn tại đây."""
    raw_state = str(raw.get("trang_thai", "")).strip().lower()
    try:
        conf = int(float(raw.get("do_tin_cay", 0)))
    except (TypeError, ValueError):
        conf = 0
    conf = max(0, min(100, conf))
    note = str(raw.get("ghi_chu", "")).strip()[:300]

    trusted = raw_state in VALID_AI_STATES and conf >= AI_MIN_CONF
    state = raw_state if trusted else "khong_xac_dinh"

    return {
        "trang_thai": state,
        "raw_state": raw_state,
        "do_tin_cay": conf,
        "trusted": trusted,
        "ghi_chu": note,
        "timestamp": time.strftime('%H:%M:%S'),
        "soil_at_capture": soil,
    }


def diagnose_leaf(image_path, soil=None):
    uploaded = client.files.upload(file=image_path)
    response = client.models.generate_content(model=MODEL_NAME, contents=[PROMPT, uploaded])
    text = re.sub(r'```json|```', '', response.text or '').strip()
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        raw = {"trang_thai": "", "do_tin_cay": 0, "ghi_chu": f"AI trả về sai định dạng: {text[:120]}"}
    return normalize_ai_result(raw, soil)


def update_camera_health(result):
    """BLOCKER 1 — phát hiện camera chĩa sai chỗ / che khuất.

    Không sửa được bằng phần mềm, nhưng phải KÊU LÊN thay vì im lặng báo
    'bình thường'. Sau CAMERA_BLIND_THRESHOLD lần liên tiếp không nhận diện
    được cây, dashboard hiện băng cảnh báo đỏ."""
    global camera_blind_streak, camera_alert
    with state_lock:
        if result["trusted"]:
            if camera_blind_streak >= CAMERA_BLIND_THRESHOLD:
                print(f"{C_GREEN}✅ Camera đã nhận diện lại được cây.{C_RESET}")
            camera_blind_streak = 0
            camera_alert = None
        else:
            camera_blind_streak += 1
            if camera_blind_streak >= CAMERA_BLIND_THRESHOLD:
                camera_alert = (
                    f"Camera không nhận diện được cây {camera_blind_streak} lần liên tiếp. "
                    f"AI ghi chú: \"{result['ghi_chu'][:90]}\". "
                    f"Kiểm tra hướng camera, ánh sáng và khoảng cách tới khay rau."
                )
        streak, alert = camera_blind_streak, camera_alert
    if alert and streak == CAMERA_BLIND_THRESHOLD:
        print(f"{C_RED}{C_BOLD}🚨 [CAMERA] {alert}{C_RESET}")
        log_event("camera_alert", {"streak": streak, "ghi_chu": result["ghi_chu"]})


def record_ai_result(result, source, photo_name):
    global latest_ai_result
    with state_lock:
        latest_ai_result = result
    db_exec(
        "INSERT INTO ai_diagnosis(ts,epoch,source,trang_thai,raw_state,do_tin_cay,"
        "trusted,ghi_chu,photo,soil) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), time.time(), source,
         result["trang_thai"], result["raw_state"], result["do_tin_cay"],
         1 if result["trusted"] else 0, result["ghi_chu"], photo_name,
         result.get("soil_at_capture")))
    log_event("ai_diagnosis", {"source": source, "result": {
        k: result[k] for k in ("trang_thai", "do_tin_cay", "trusted", "ghi_chu", "timestamp")}})
    update_camera_health(result)


def run_diagnosis(source):
    """Đường chạy chung cho cả chu kỳ tự động và CHECK_LEAF."""
    with state_lock:
        soil = latest_sensor.get('soil')
    path, name = capture_image()
    result = diagnose_leaf(path, soil)
    record_ai_result(result, source, name)
    emoji = AI_EMOJI.get(result['trang_thai'], "⚪")
    trust = "" if result["trusted"] else " [KHÔNG ĐÁNG TIN]"
    return result, f"{emoji} {result['trang_thai']} ({result['do_tin_cay']}%){trust} - {result['ghi_chu']}"


def ai_vision_worker():
    """Chu kỳ tự động 15 phút/lần. CHECK_LEAF là đường riêng, xem trigger_leaf_check()."""
    time.sleep(8)  # chờ có số liệu cảm biến đầu tiên để ghi kèm soil
    while True:
        try:
            print(f"{C_CYAN}📷 [AI] Đang chụp ảnh lá để chẩn đoán (chu kỳ tự động)...{C_RESET}")
            _, msg = run_diagnosis("auto_cycle")
            print(f"{C_CYAN}{C_BOLD} 🤖 [KẾT QUẢ AI] {msg} {C_RESET}")
        except Exception as e:
            print(f"{C_RED}⚠️  [AI] Lỗi chẩn đoán: {e}{C_RESET}")
            log_event("error", {"where": "ai_vision_worker", "message": str(e)})
        time.sleep(AI_CHECK_INTERVAL)


def trigger_leaf_check(source="Terminal"):
    """Lệnh CHECK_LEAF: chụp + chẩn đoán ngay, độc lập chu kỳ tự động.
    Có cooldown riêng để tránh đốt quota Gemini khi demo bấm liên tục."""
    global last_leaf_check_time
    now = time.time()
    with state_lock:
        remaining = CHECK_LEAF_COOLDOWN - (now - last_leaf_check_time)
        if remaining > 0:
            return False, f"Vừa chụp xong, chờ thêm {int(remaining) + 1}s để tránh tốn quota Gemini"
        last_leaf_check_time = now

    print(f"{C_CYAN}📷 [CHECK_LEAF] Yêu cầu chẩn đoán ngay từ {source}...{C_RESET}")
    try:
        _, msg = run_diagnosis(f"check_leaf:{source}")
        print(f"{C_CYAN}{C_BOLD} 🤖 [CHECK_LEAF] {msg} {C_RESET}")
        return True, msg
    except Exception as e:
        print(f"{C_RED}⚠️  [CHECK_LEAF] Lỗi chẩn đoán: {e}{C_RESET}")
        log_event("error", {"where": f"check_leaf:{source}", "message": str(e)})
        return False, f"Lỗi chẩn đoán: {e}"


# ==================== ĐỌC TRẠNG THÁI ĐẤT ====================
def read_soil_state():
    """Trả về (soil_pct, is_dry, is_fresh).
    is_fresh = False nghĩa là mất số liệu ESP32 -> fusion phải xử lý thận trọng."""
    now = time.time()
    with state_lock:
        soil = latest_sensor.get('soil')
        age = now - last_sensor_time if last_sensor_time else None
    fresh = age is not None and age <= SENSOR_STALE_SEC
    if not fresh or soil is None:
        return soil, None, False
    try:
        soil = int(soil)
    except (TypeError, ValueError):
        return None, None, False
    return soil, soil < SOIL_DRY_THRESHOLD, True


# ==================== MỨC 1 — AI KHẨN CẤP + FUSION ====================
def check_ai_emergency():
    """MỨC 1 — luôn gọi độc lập mỗi vòng lặp, KHÔNG bị chặn bởi Time Guard
    hay Manual Override. Trả về (cmds, reason, level) hoặc None.

    Khác v1: kết hợp độ ẩm đất trước khi quyết định tưới. Héo rũ mà đất còn ẩm
    là dấu hiệu thối rễ hoặc sốc nhiệt — tưới thêm sẽ giết cây nhanh hơn."""
    with state_lock:
        ai = dict(latest_ai_result) if latest_ai_result else None

    if not (ai and ai.get('trusted')
            and ai.get('trang_thai') == 'heo_ru'
            and ai.get('do_tin_cay', 0) >= AI_EMERGENCY_CONF):
        return None

    soil, is_dry, fresh = read_soil_state()
    conf = ai['do_tin_cay']

    # Đất còn ẩm -> nghi thối rễ: KHOÁ, không tưới.
    if fresh and is_dry is False:
        if pulse("rootrot_hold", ROOTROT_HOLD_DURATION, ROOTROT_COOLDOWN):
            return (["LOCK_IDLE"],
                    f"🚨 NGHI THỐI RỄ: AI báo héo rũ ({conf}%) nhưng đất còn ẩm {soil}% "
                    f"→ KHOÁ tưới {ROOTROT_HOLD_DURATION // 60} phút, kiểm tra rễ và thoát nước",
                    "1-KHẨN CẤP")
        return None  # hết cửa sổ khoá -> nhường cho các mức dưới

    # Đất khô hoặc mất số liệu -> tưới xung có thời hạn.
    soil_txt = f"đất {soil}%" if fresh else "không có số liệu đất"
    if pulse("emergency_water", EMERGENCY_WATER_DURATION, AI_EMERGENCY_COOLDOWN):
        remain = pulse_remaining("emergency_water")
        log_event("emergency_watering",
                  {"do_tin_cay": conf, "soil": soil, "ghi_chu": ai.get('ghi_chu')})
        return (["WATER_ON"],
                f"🚨 KHẨN CẤP: AI phát hiện héo rũ ({conf}%), {soil_txt} "
                f"→ tưới {EMERGENCY_WATER_DURATION}s (còn {remain}s)",
                "1-KHẨN CẤP")
    return None  # đã tưới xong hoặc đang cooldown -> trả quyền cho mức dưới


# ==================== MỨC 4 — MA TRẬN FUSION ====================
def decide_fusion():
    """MỨC 4-5 — chỉ gọi khi KHÔNG khẩn cấp, KHÔNG ban đêm, KHÔNG override tay.

    Ma trận quyết định = f(trạng thái AI, độ ẩm đất). Trả về (cmds, reason, level).
    Chỉ tin AI khi result['trusted'] = True."""
    with state_lock:
        ai = dict(latest_ai_result) if latest_ai_result else None
    soil, is_dry, fresh = read_soil_state()
    soil_txt = f"đất {soil}%" if fresh else "chưa có số liệu đất"

    state = ai.get('trang_thai') if (ai and ai.get('trusted')) else 'khong_xac_dinh'
    conf = ai.get('do_tin_cay', 0) if ai else 0

    # --- ĐỐM NÂU: nấm. Cấm phun sương, vẫn cho tưới gốc theo ngưỡng ESP32. ---
    if state == 'dom_nau':
        return (["MIST_LOCK", "AUTO"],
                f"🟠 AI phát hiện đốm nâu ({conf}%) → CẤM phun sương (nấm gặp ẩm sẽ lan), "
                f"tưới gốc vẫn theo ngưỡng cảm biến · {soil_txt}",
                "4-FUSION")

    # --- HÉO RŨ tin cậy thấp (chưa tới ngưỡng khẩn cấp) ---
    if state == 'heo_ru':
        if fresh and is_dry:
            return (["MIST_UNLOCK", "AUTO"],
                    f"🔴 AI báo héo rũ ({conf}%) + {soil_txt} khô → để ESP32 tưới theo ngưỡng, đang theo dõi",
                    "4-FUSION")
        return (["MIST_UNLOCK", "AUTO"],
                f"🔴 AI báo héo rũ ({conf}%) nhưng {soil_txt} → chưa đủ tin cậy để can thiệp, "
                f"cần kiểm tra rễ và bóng râm bằng mắt",
                "4-FUSION")

    # --- VÀNG LÁ: phân biệt thiếu nước với thiếu dinh dưỡng ---
    if state == 'vang_la':
        if fresh and is_dry is False:
            return (["MIST_UNLOCK", "AUTO"],
                    f"🟡 AI phát hiện vàng lá ({conf}%) nhưng {soil_txt} còn ẩm → nghi THIẾU ĐẠM, "
                    f"không phải thiếu nước · cần bổ sung dinh dưỡng, không tưới thêm",
                    "4-FUSION")
        return (["MIST_UNLOCK", "AUTO"],
                f"🟡 AI phát hiện vàng lá ({conf}%) + {soil_txt} → để ESP32 tưới theo ngưỡng",
                "4-FUSION")

    # --- KHÔNG XÁC ĐỊNH: không được phép ảnh hưởng cơ cấu chấp hành ---
    if state == 'khong_xac_dinh':
        with state_lock:
            alert = camera_alert
        extra = " · ⚠️ nghi camera lệch hướng" if alert else ""
        return (["MIST_UNLOCK", "AUTO"],
                f"⚪ Chưa có chẩn đoán đáng tin (AI {conf}%) → chạy hoàn toàn theo cảm biến{extra} · {soil_txt}",
                "5-MẶC ĐỊNH")

    # --- BÌNH THƯỜNG ---
    return (["MIST_UNLOCK", "AUTO"],
            f"✅ Cây bình thường ({conf}%) · {soil_txt} → ESP32 tự quyết theo cảm biến",
            "5-MẶC ĐỊNH")


# ==================== GỬI LỆNH ====================
def send_command(sm, cmd, reason="", level="", force=False):
    global last_sent_cmd, last_sent_reason, last_decision_level, mist_locked
    with state_lock:
        if cmd == "MIST_LOCK":
            if mist_locked and not force:
                return
            mist_locked = True
        elif cmd == "MIST_UNLOCK":
            if not mist_locked and not force:
                return
            mist_locked = False
        else:
            if cmd == last_sent_cmd and not force:
                last_sent_reason, last_decision_level = reason, level
                return
            last_sent_cmd = cmd
        last_sent_reason, last_decision_level = reason, level

    sm.write(f"{cmd}\n".encode())
    db_exec("INSERT INTO commands(ts,epoch,cmd,level,reason) VALUES(?,?,?,?,?)",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), time.time(), cmd, level, reason))
    print(f"\n{C_YELLOW}{C_BOLD} 🚀 [{level}] → ESP32: {cmd} | {reason} {C_RESET}\n")


def send_plan(sm, cmds, reason, level):
    """Một quyết định có thể gồm nhiều lệnh (ví dụ MIST_LOCK rồi AUTO)."""
    for c in cmds:
        send_command(sm, c, reason, level)


def apply_manual_command(sm, cmd, source="Web Dashboard"):
    """Dùng chung cho MỌI nguồn điều khiển actuator thủ công.
    KHÔNG dùng cho CHECK_LEAF — đó không phải lệnh actuator."""
    global manual_override_until
    cmd = (cmd or "").strip().upper()
    if cmd not in MANUAL_COMMANDS:
        return False, f"Lệnh không hợp lệ: {cmd}"

    if cmd == "AUTO":
        with state_lock:
            manual_override_until = 0.0
        send_command(sm, "AUTO", f"{source}: trả về chế độ tự động", "3-THỦ CÔNG", force=True)
    else:
        with state_lock:
            manual_override_until = time.time() + MANUAL_OVERRIDE_DURATION
        send_command(sm, cmd,
                     f"{source}: lệnh thủ công (override {MANUAL_OVERRIDE_DURATION // 60} phút)",
                     "3-THỦ CÔNG", force=True)
    log_event("manual_command", {"cmd": cmd, "source": source})
    return True, f"Đã gửi lệnh {cmd}"


# ==================== VÒNG LẶP QUYẾT ĐỊNH ====================
def decision_loop(sm):
    global last_ping_time
    while True:
        try:
            now = time.time()
            if now - last_ping_time >= PING_INTERVAL:
                last_ping_time = now
                sm.write(b"PING\n")   # nuôi watchdog firmware v2.1, không đổi trạng thái

            emergency = check_ai_emergency()
            if emergency:
                send_plan(sm, *emergency)
            elif is_nighttime():
                send_command(sm, 'LOCK_IDLE',
                             f"🌙 Time Guard: khung giờ bảo vệ ban đêm ({NIGHT_START_HOUR}h-{NIGHT_END_HOUR}h)",
                             "2-TIME GUARD")
            else:
                with state_lock:
                    override_active = time.time() < manual_override_until
                if not override_active:
                    send_plan(sm, *decide_fusion())
                # else: đang override thủ công hợp lệ -> giữ nguyên
        except Exception as e:
            print(f"{C_RED}⚠️  Lỗi decision_loop: {e}{C_RESET}")
            log_event("error", {"where": "decision_loop", "message": str(e)})
        time.sleep(DECISION_LOOP_INTERVAL)


# ==================== ĐỌC SERIAL & HIỂN THỊ ====================
def print_sensor_status(sensor):
    temp, humi = sensor.get('temp', 0.0), sensor.get('humi', 0)
    soil, light = sensor.get('soil', 0), sensor.get('light', 0)
    w = str(sensor.get('water', 'false')).lower() == 'true'
    m = str(sensor.get('mist', 'false')).lower() == 'true'
    water = f"{C_GREEN}[BẬT]{C_RESET}" if w else f"{C_RED}[TẮT]{C_RESET}"
    mist = f"{C_GREEN}[BẬT]{C_RESET}" if m else f"{C_RED}[TẮT]{C_RESET}"
    mode_raw = sensor.get('mode', 'AUTO')
    mode_str = f"{C_CYAN}{mode_raw}{C_RESET}" if mode_raw == "AUTO" else f"{C_YELLOW}{mode_raw}{C_RESET}"

    with state_lock:
        ai = latest_ai_result
        lock = mist_locked
        alert = camera_alert

    print(f"{C_BOLD}[{time.strftime('%H:%M:%S')}] ── CHẾ ĐỘ: {mode_str}{C_RESET}")
    print(f"  ├─ {C_BLUE}CẢM BIẾN{C_RESET} : Nhiệt {temp}°C | Ẩm KK {humi}% | Đất {soil}% | Sáng {light}%")
    print(f"  ├─ {C_BLUE}THIẾT BỊ{C_RESET} : Bơm gốc {water} | Phun sương {mist}"
          + (f" {C_YELLOW}[SƯƠNG ĐANG BỊ KHOÁ]{C_RESET}" if lock else ""))
    print(f"  ├─ {C_BLUE}LÝ DO (ESP32){C_RESET}: {sensor.get('reason', 'N/A')}")
    if ai:
        emoji = AI_EMOJI.get(ai.get('trang_thai'), "⚪")
        trust = "" if ai.get('trusted') else f" {C_RED}[không đáng tin]{C_RESET}"
        print(f"  └─ {C_BLUE}AI ({ai.get('timestamp', '?')}){C_RESET}: "
              f"{emoji} {ai.get('trang_thai')} ({ai.get('do_tin_cay')}%){trust} - {ai.get('ghi_chu', '')}")
    else:
        print(f"  └─ {C_BLUE}AI{C_RESET}: chưa có dữ liệu chẩn đoán")
    if alert:
        print(f"     {C_RED}{C_BOLD}🚨 {alert}{C_RESET}")
    print("-" * 78)


def serial_reader(sm):
    global latest_sensor, last_sensor_time, last_history_sample_time, last_db_sensor_time
    while True:
        raw = sm.readline()
        line = raw.decode('utf-8', errors='ignore').strip()
        if not line or not line.startswith('{'):
            continue
        try:
            sensor = json.loads(line)
        except json.JSONDecodeError:
            continue

        # ESP32 còn gửi gói sự kiện, ví dụ {"event":"watchdog","detail":"..."}.
        # Nếu nhận nhầm là gói cảm biến thì latest_sensor bị ghi đè và toàn bộ
        # số liệu nhiệt/ẩm/đất biến thành rỗng trên dashboard.
        if 'temp' not in sensor:
            if sensor.get('event'):
                print(f"{C_YELLOW}⚠️  [ESP32] {sensor.get('event')}: {sensor.get('detail', '')}{C_RESET}")
                log_event("esp32_event", {"event": sensor.get('event'),
                                          "detail": sensor.get('detail')})
            continue

        now = time.time()
        do_db = False
        with state_lock:
            latest_sensor = sensor
            last_sensor_time = now
            if now - last_history_sample_time >= HISTORY_SAMPLE_INTERVAL:
                last_history_sample_time = now
                sensor_history.append({
                    "t": time.strftime('%H:%M:%S'),
                    "temp": sensor.get('temp'), "humi": sensor.get('humi'),
                    "soil": sensor.get('soil'), "light": sensor.get('light'),
                })
            if now - last_db_sensor_time >= DB_SENSOR_INTERVAL:
                last_db_sensor_time = now
                do_db = True

        if do_db:
            db_exec(
                "INSERT INTO sensor_readings(ts,epoch,temp,humi,soil,light,water,mist,mode) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), now,
                 sensor.get('temp'), sensor.get('humi'), sensor.get('soil'), sensor.get('light'),
                 1 if str(sensor.get('water')).lower() == 'true' else 0,
                 1 if str(sensor.get('mist')).lower() == 'true' else 0,
                 sensor.get('mode')))
        print_sensor_status(sensor)


# ==================== LỆNH THỦ CÔNG (TERMINAL) ====================
def input_listener(sm):
    print(f"{C_BLUE}Lệnh: WATER_ON | WATER_OFF | MIST_ON | MIST_OFF | AUTO | LOCK_IDLE | CHECK_LEAF{C_RESET}")
    while True:
        try:
            cmd = input().strip().upper()
        except EOFError:
            time.sleep(1)
            continue
        if not cmd:
            continue
        if cmd == "CHECK_LEAF":
            ok, msg = trigger_leaf_check(source="Terminal")
            print(f"{C_GREEN if ok else C_RED}{msg}{C_RESET}")
            continue
        ok, msg = apply_manual_command(sm, cmd, source="Terminal")
        if not ok:
            print(f"{C_RED}{msg}{C_RESET}")


# ==================== WEB DASHBOARD (FLASK) ====================
app = Flask(__name__)
_dashboard_sm = None


@app.route('/')
def dashboard_index():
    return send_file(os.path.join(BASE_DIR, 'templates', 'dashboard.html'))


@app.route('/api/status')
def api_status():
    now = time.time()
    with state_lock:
        sensor = dict(latest_sensor)
        ai = dict(latest_ai_result) if latest_ai_result else None
        override_remaining = max(0, int(manual_override_until - now))
        cmd, reason, level = last_sent_cmd, last_sent_reason, last_decision_level
        sensor_age = round(now - last_sensor_time, 1) if last_sensor_time else None
        check_leaf_remaining = max(0, int(CHECK_LEAF_COOLDOWN - (now - last_leaf_check_time)))
        lock, alert, streak = mist_locked, camera_alert, camera_blind_streak
        photo = last_photo_name

    soil, is_dry, fresh = read_soil_state()
    return jsonify({
        "sensor": sensor,
        "ai": ai,
        "last_cmd": cmd,
        "last_reason": reason,
        "decision_level": level,
        "manual_override_remaining": override_remaining,
        "check_leaf_cooldown_remaining": check_leaf_remaining,
        "sensor_age_sec": sensor_age,
        "is_night": is_nighttime(),
        "mist_locked": lock,
        "camera_alert": alert,
        "camera_blind_streak": streak,
        "latest_photo": photo,
        "soil_is_dry": is_dry,
        "soil_fresh": fresh,
        "soil_threshold": SOIL_DRY_THRESHOLD,
        "emergency_water_remaining": pulse_remaining("emergency_water"),
        "rootrot_hold_remaining": pulse_remaining("rootrot_hold"),
        "server_time": time.strftime('%H:%M:%S'),
    })


@app.route('/api/history')
def api_history():
    """minutes<=60 -> lấy từ RAM (mượt, 15s/điểm).
    Lớn hơn -> truy vấn SQLite và lấy mẫu thưa để không quá 300 điểm."""
    try:
        minutes = max(5, min(10080, int(request.args.get('minutes', 60))))
    except ValueError:
        minutes = 60

    if minutes <= 60:
        with state_lock:
            hist = list(sensor_history)
        cut = (minutes * 60) // HISTORY_SAMPLE_INTERVAL
        return jsonify({"history": hist[-cut:], "source": "ram", "minutes": minutes})

    rows = db_query(
        "SELECT ts,temp,humi,soil,light FROM sensor_readings WHERE epoch >= ? ORDER BY epoch ASC",
        (time.time() - minutes * 60,))
    step = max(1, len(rows) // 300)
    hist = [{"t": r["ts"][5:16], "temp": r["temp"], "humi": r["humi"],
             "soil": r["soil"], "light": r["light"]} for r in rows[::step]]
    return jsonify({"history": hist, "source": "sqlite", "minutes": minutes, "total_rows": len(rows)})


@app.route('/api/image')
def api_image():
    if not os.path.exists(LATEST_IMG):
        return jsonify({"error": "Chưa có ảnh nào được chụp"}), 404
    resp = send_file(LATEST_IMG, mimetype='image/jpeg')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp


@app.route('/api/photos')
def api_photos():
    files = sorted(glob.glob(os.path.join(PHOTO_DIR, 'leaf_*.jpg')), reverse=True)[:PHOTO_KEEP]
    rows = db_query("SELECT photo,trang_thai,do_tin_cay,trusted,ghi_chu,ts FROM ai_diagnosis "
                    "WHERE photo IS NOT NULL ORDER BY epoch DESC LIMIT ?", (PHOTO_KEEP,))
    meta = {r["photo"]: r for r in rows}
    return jsonify({"photos": [
        {"name": os.path.basename(f), **{k: meta.get(os.path.basename(f), {}).get(k)
                                         for k in ("trang_thai", "do_tin_cay", "trusted", "ghi_chu", "ts")}}
        for f in files]})


@app.route('/api/photo/<name>')
def api_photo(name):
    if not re.fullmatch(r'leaf_\d{8}_\d{6}\.jpg', name):
        return jsonify({"error": "Tên file không hợp lệ"}), 400
    path = os.path.join(PHOTO_DIR, name)
    if not os.path.exists(path):
        return jsonify({"error": "Không tìm thấy ảnh"}), 404
    return send_file(path, mimetype='image/jpeg')


@app.route('/api/events')
def api_events():
    try:
        limit = max(1, min(500, int(request.args.get('limit', 60))))
    except ValueError:
        limit = 60
    return jsonify({"events": db_query(
        "SELECT ts,event,detail FROM events ORDER BY epoch DESC LIMIT ?", (limit,))})


@app.route('/api/diagnosis')
def api_diagnosis():
    try:
        limit = max(1, min(500, int(request.args.get('limit', 30))))
    except ValueError:
        limit = 30
    return jsonify({"diagnosis": db_query(
        "SELECT ts,source,trang_thai,do_tin_cay,trusted,ghi_chu,photo,soil "
        "FROM ai_diagnosis ORDER BY epoch DESC LIMIT ?", (limit,))})


@app.route('/api/export.csv')
def api_export_csv():
    """Xuất số liệu cảm biến ra CSV — dùng để vẽ biểu đồ trong báo cáo."""
    try:
        hours = max(1, min(720, int(request.args.get('hours', 24))))
    except ValueError:
        hours = 24
    rows = db_query("SELECT ts,temp,humi,soil,light,water,mist,mode FROM sensor_readings "
                    "WHERE epoch >= ? ORDER BY epoch ASC", (time.time() - hours * 3600,))

    def gen():
        yield "ts,temp,humi,soil,light,water,mist,mode\n"
        for r in rows:
            yield (f'{r["ts"]},{r["temp"]},{r["humi"]},{r["soil"]},{r["light"]},'
                   f'{r["water"]},{r["mist"]},{r["mode"]}\n')

    return Response(gen(), mimetype='text/csv', headers={
        'Content-Disposition': f'attachment; filename=smart_garden_{hours}h.csv'})


@app.route('/api/stats')
def api_stats():
    """Số liệu tổng hợp cho mục 3.5 Testing của báo cáo."""
    return jsonify({
        "sensor_rows": db_query("SELECT COUNT(*) c FROM sensor_readings")[0]["c"],
        "ai_total": db_query("SELECT COUNT(*) c FROM ai_diagnosis")[0]["c"],
        "ai_trusted": db_query("SELECT COUNT(*) c FROM ai_diagnosis WHERE trusted=1")[0]["c"],
        "by_state": db_query("SELECT trang_thai, COUNT(*) c FROM ai_diagnosis "
                             "WHERE trusted=1 GROUP BY trang_thai"),
        "emergency_count": db_query(
            "SELECT COUNT(*) c FROM events WHERE event='emergency_watering'")[0]["c"],
        "camera_alerts": db_query(
            "SELECT COUNT(*) c FROM events WHERE event='camera_alert'")[0]["c"],
        "first_record": db_query("SELECT MIN(ts) t FROM sensor_readings")[0]["t"],
    })


@app.route('/api/command', methods=['POST'])
def api_command():
    data = request.get_json(silent=True) or {}
    ok, msg = apply_manual_command(_dashboard_sm, data.get('cmd', ''), source="Web Dashboard")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 400)


@app.route('/api/check_leaf', methods=['POST'])
def api_check_leaf():
    ok, msg = trigger_leaf_check(source="Web Dashboard")
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 429)


def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def dashboard_worker(sm):
    global _dashboard_sm
    _dashboard_sm = sm
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, threaded=True, use_reloader=False)


# ============================== MAIN ==============================
def main():
    os.makedirs(PHOTO_DIR, exist_ok=True)
    db_init()
    db_restore_history()

    sm = SerialManager()
    lan_ip = get_lan_ip()

    print(f"{C_CYAN}{C_BOLD}")
    print("=" * 78)
    print(" 🌿 SMART HOME GARDEN v2 — GIÁM SÁT & ĐIỀU KHIỂN THÔNG MINH 🌿")
    print(" Ưu tiên: AI khẩn cấp > Time Guard > Manual > Ma trận fusion > Mặc định")
    print(f" AI tự động mỗi {AI_CHECK_INTERVAL // 60} phút | Ngưỡng tin cậy {AI_MIN_CONF}% | "
          f"Khẩn cấp {AI_EMERGENCY_CONF}%")
    print(f" Tưới khẩn cấp {EMERGENCY_WATER_DURATION}s rồi tự trả AUTO | "
          f"Ngưỡng đất khô {SOIL_DRY_THRESHOLD}%")
    print(f" 🌐 Dashboard: http://{lan_ip}:{DASHBOARD_PORT}")
    print(f" 💾 SQLite: {DB_PATH}")
    print(f" 📷 Kho ảnh: {PHOTO_DIR} (giữ {PHOTO_KEEP} ảnh gần nhất)")
    print("=" * 78 + C_RESET + "\n")

    log_event("startup", {"lan_ip": lan_ip, "version": "2.0"})

    threading.Thread(target=serial_reader, args=(sm,), daemon=True).start()
    threading.Thread(target=ai_vision_worker, daemon=True).start()
    threading.Thread(target=dashboard_worker, args=(sm,), daemon=True).start()

    if sys.stdin.isatty():
        threading.Thread(target=input_listener, args=(sm,), daemon=True).start()
    else:
        print(f"{C_BLUE}(Chạy dưới dạng service — không có input thủ công qua terminal){C_RESET}")

    decision_loop(sm)


if __name__ == '__main__':
    main()
