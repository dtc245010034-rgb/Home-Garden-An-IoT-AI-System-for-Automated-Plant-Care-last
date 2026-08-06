"""Nạp main.py để kiểm thử mà không cần ESP32, camera, API key hay mạng.

Ba thư viện phần cứng (cv2, serial, google.genai) được thay bằng module giả
TRƯỚC khi import main, nên bộ kiểm thử chạy được trên máy không cài gì thêm.
Dữ liệu ghi vào thư mục tạm qua SG_DATA_DIR, không đụng smart_garden.db thật.
"""
import importlib
import sys
import types
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))


def _module_gia(ten, **thuoc_tinh):
    m = types.ModuleType(ten)
    for k, v in thuoc_tinh.items():
        setattr(m, k, v)
    return m


class _SerialExceptionGia(Exception):
    pass


def _cai_module_gia():
    sys.modules.setdefault('cv2', _module_gia(
        'cv2', VideoCapture=lambda *a, **k: None, imwrite=lambda *a, **k: True,
        CAP_PROP_FRAME_WIDTH=3, CAP_PROP_FRAME_HEIGHT=4))
    sys.modules.setdefault('serial', _module_gia(
        'serial', Serial=lambda *a, **k: None, SerialException=_SerialExceptionGia))
    google = sys.modules.get('google') or _module_gia('google')
    genai = _module_gia('genai', Client=lambda **k: None)
    google.genai = genai
    sys.modules.setdefault('google', google)
    sys.modules.setdefault('google.genai', genai)


@pytest.fixture(scope='session')
def sg(tmp_path_factory):
    """Trả về module main đã nạp, dữ liệu nằm trong thư mục tạm."""
    data = tmp_path_factory.mktemp('sg_data')
    import os
    os.environ['SG_DATA_DIR'] = str(data)
    # Bật cổng chặn chế độ kiểm thử, nếu không thì việc ép giờ sẽ vô tác dụng —
    # đúng như thiết kế khi chạy thật.
    os.environ['SG_TEST_MODE'] = '1'
    _cai_module_gia()
    m = importlib.import_module('main')
    m.db_init()
    return m


@pytest.fixture(autouse=True)
def _sach(sg):
    """Mỗi bài test bắt đầu từ trạng thái sạch."""
    with sg.state_lock:
        sg.latest_sensor = {}
        sg.latest_ai_result = None
        sg.last_sensor_time = 0.0
        sg.last_sent_cmd = None
        sg.mist_locked = False
        sg.manual_override_until = 0.0
        sg.camera_alert = None
        sg.camera_blind_streak = 0
    sg.pulse_state.clear()
    sg.last_ping_time = 0.0
    sg.test_force_night = None
    yield


class ESP32Gia:
    """Thay cho SerialManager. Ghi lại mọi lệnh Pi gửi xuống và phát telemetry."""

    def __init__(self, khung=None):
        self.da_nhan = []          # danh sách lệnh đã nhận, theo thứ tự
        self.khung = list(khung or [])

    def write(self, data: bytes):
        self.da_nhan.append(data.decode().strip())

    def readline(self) -> bytes:
        if self.khung:
            return (self.khung.pop(0) + '\n').encode()
        return b''

    @property
    def lenh(self):
        """Các lệnh thật, bỏ nhịp tim PING cho dễ khẳng định."""
        return [c for c in self.da_nhan if c != 'PING']


@pytest.fixture
def esp32():
    return ESP32Gia()


@pytest.fixture
def dat_cam_bien(sg):
    """Đặt số đo cảm biến như vừa nhận được từ ESP32."""
    def _dat(soil=None, temp=28.0, light=50, tuoi=0.0, **extra):
        with sg.state_lock:
            sg.latest_sensor = {"temp": temp, "humi": 70, "soil": soil,
                                "light": light, "water": "false", "mist": "false",
                                "mode": "AUTO", "reason": "test", **extra}
            sg.last_sensor_time = sg.time.time() - tuoi
    return _dat


@pytest.fixture
def dat_ai(sg):
    """Đặt kết quả chẩn đoán AI đã qua chuẩn hoá."""
    def _dat(trang_thai, do_tin_cay, soil=None):
        r = sg.normalize_ai_result(
            {"trang_thai": trang_thai, "do_tin_cay": do_tin_cay, "ghi_chu": "test"}, soil)
        with sg.state_lock:
            sg.latest_ai_result = r
        return r
    return _dat
