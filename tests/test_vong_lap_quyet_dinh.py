"""Chạy thật một vòng của decision_loop với ESP32 giả.

Kiểm tra những thứ chỉ lộ ra khi các phần ghép lại: thứ tự năm mức ưu tiên, lọc
lệnh trùng, nhịp PING, và bảo đảm không lệnh ép nào chạy vô thời hạn.
"""
import pytest

KHO, AM = 25, 75


def mot_vong(sg, esp32):
    """Gọi thẳng decision_tick() thật của main.py.

    Trước đây hàm này chép lại logic vòng lặp, hậu quả là xoá PING khỏi code thật
    mà test vẫn xanh. Kiểm thử đột biến phát hiện ra điều đó."""
    sg.decision_tick(esp32)


# ------------------------------------------------- thứ tự ưu tiên
def test_ban_dem_khoa_va_lenh_tay_khong_ghi_de_duoc(sg, esp32, dat_cam_bien):
    """Time Guard ở mức 2, override tay ở mức 3. Bấm tưới ban đêm phải vô hiệu."""
    dat_cam_bien(soil=KHO)
    sg.test_force_night = True

    ok, _ = sg.apply_manual_command(esp32, "WATER_ON", source="test")
    assert ok, "lệnh vẫn được nhận và ghi log"
    mot_vong(sg, esp32)

    assert esp32.lenh[-1] == "LOCK_IDLE", (
        "vòng kế tiếp phải khoá lại, lệnh tay không thắng được Time Guard")


def test_khan_cap_thang_ca_lenh_tay(sg, esp32, dat_cam_bien, dat_ai):
    """AI khẩn cấp ở mức 1, trên cả override tay."""
    dat_cam_bien(soil=AM)
    dat_ai("heo_ru", 95, AM)
    sg.apply_manual_command(esp32, "WATER_ON", source="test")
    mot_vong(sg, esp32)
    assert esp32.lenh[-1] == "LOCK_IDLE", "nghi thối rễ phải thắng lệnh tưới tay"


def test_ban_ngay_khong_khan_cap_thi_theo_lenh_tay(sg, esp32, dat_cam_bien):
    dat_cam_bien(soil=KHO)
    sg.test_force_night = False
    sg.apply_manual_command(esp32, "WATER_ON", source="test")
    truoc = list(esp32.lenh)
    mot_vong(sg, esp32)
    assert esp32.lenh == truoc, "đang trong thời hạn override thì không được ghi đè"


# ------------------------------------------------- lọc lệnh trùng và PING
def test_lenh_trung_khong_phat_lai(sg, esp32, dat_cam_bien):
    dat_cam_bien(soil=AM)
    sg.test_force_night = False
    for _ in range(5):
        mot_vong(sg, esp32)
    assert esp32.lenh.count("AUTO") == 1, "AUTO chỉ được phát một lần, sau đó bị lọc"


def test_co_nhip_ping_khi_quyet_dinh_giu_nguyen(sg, esp32, dat_cam_bien):
    """Đây chính là khiếm khuyết số 10. Quyết định giữ nguyên vẫn phải sinh PING,
    nếu không watchdog ESP32 sẽ tưởng Pi chết và huỷ khoá ban đêm."""
    dat_cam_bien(soil=KHO)
    sg.test_force_night = True

    mot_vong(sg, esp32)
    sg.last_ping_time -= sg.PING_INTERVAL + 1     # giả lập 10 giây trôi qua
    mot_vong(sg, esp32)
    sg.last_ping_time -= sg.PING_INTERVAL + 1
    mot_vong(sg, esp32)

    assert esp32.da_nhan.count("PING") >= 3, (
        "thiếu PING thì khoá ban đêm bị watchdog nhả sau 60 giây")
    assert esp32.lenh.count("LOCK_IDLE") == 1, "LOCK_IDLE vẫn chỉ phát một lần"


# ------------------------------------------------- an toàn thời hạn
def test_tuoi_khan_cap_tu_het_han_va_tra_ve_auto(sg, esp32, dat_cam_bien, dat_ai):
    dat_cam_bien(soil=KHO)
    dat_ai("heo_ru", 95, KHO)
    mot_vong(sg, esp32)
    assert esp32.lenh[-1] == "WATER_ON"

    # đẩy đồng hồ xung qua thời hạn 60 giây
    p = sg.pulse_state["emergency_water"]
    p["until"] = sg.time.time() - 1
    mot_vong(sg, esp32)

    assert esp32.lenh[-1] == "AUTO", "hết 60 giây phải tự trả về AUTO"
    assert sg.pulse_remaining("emergency_water") == 0


def test_cooldown_chan_tuoi_lien_tuc_cung_trieu_chung(sg, esp32, dat_cam_bien, dat_ai):
    dat_cam_bien(soil=KHO)
    dat_ai("heo_ru", 95, KHO)
    mot_vong(sg, esp32)
    p = sg.pulse_state["emergency_water"]
    p["until"] = sg.time.time() - 1        # hết xung, còn trong cooldown
    for _ in range(5):
        mot_vong(sg, esp32)
    assert esp32.lenh.count("WATER_ON") == 1, "cooldown 1 giờ phải chặn xung thứ hai"


def test_chu_ky_ping_phai_du_ngan_so_voi_watchdog(sg):
    """Bất biến ghép hai tầng: firmware huỷ trạng thái sau 60 giây im lặng.
    Nhịp tim phải kịp phát ít nhất hai lần trong cửa sổ đó, để mất một nhịp
    vẫn chưa nổ watchdog. Kiểm thử đột biến cho thấy nếu thiếu bài này thì
    đổi PING_INTERVAL thành 3600 mà cả bộ test vẫn xanh."""
    WATCHDOG_GIAY = 60          # SERIAL_WATCHDOG_MS trong firmware/v2/v2.ino
    assert sg.PING_INTERVAL * 2 < WATCHDOG_GIAY, (
        f"PING mỗi {sg.PING_INTERVAL}s là quá thưa so với watchdog {WATCHDOG_GIAY}s")


def test_mist_lock_khong_phat_lai_khi_da_khoa(sg, esp32):
    """MIST_LOCK đi theo cờ mist_locked chứ không theo last_sent_cmd,
    nên cần bài riêng: nhánh dedupe của nó là một nhánh khác."""
    sg.send_command(esp32, "MIST_LOCK", "lần đầu", "4-FUSION")
    sg.send_command(esp32, "MIST_LOCK", "lần hai", "4-FUSION")
    assert esp32.lenh.count("MIST_LOCK") == 1, "đang khoá rồi thì không phát lại"

    sg.send_command(esp32, "MIST_UNLOCK", "mở khoá", "5-MẶC ĐỊNH")
    sg.send_command(esp32, "MIST_UNLOCK", "mở lại", "5-MẶC ĐỊNH")
    assert esp32.lenh.count("MIST_UNLOCK") == 1, "đã mở rồi thì không phát lại"

    sg.send_command(esp32, "MIST_LOCK", "khoá lại", "4-FUSION")
    assert esp32.lenh.count("MIST_LOCK") == 2, "đổi trạng thái thật thì phải phát"


def test_khong_lenh_ep_nao_ton_tai_vo_thoi_han(sg):
    """Quét mọi xung được khai báo: cái nào cũng phải có hạn."""
    for ten, thoi_han, cooldown in [
            ("emergency_water", sg.EMERGENCY_WATER_DURATION, sg.AI_EMERGENCY_COOLDOWN),
            ("rootrot_hold", sg.ROOTROT_HOLD_DURATION, sg.ROOTROT_COOLDOWN)]:
        sg.pulse_state.clear()
        assert sg.pulse(ten, thoi_han, cooldown) is True
        assert 0 < sg.pulse_remaining(ten) <= thoi_han
        sg.pulse_state[ten]["until"] = sg.time.time() - 1
        assert sg.pulse(ten, thoi_han, cooldown) is False, "hết hạn thì phải vào cooldown"


def test_thoi_han_ep_actuator_nam_trong_gioi_han_hop_ly(sg):
    """pulse() bảo đảm 'có thời hạn', nhưng thời hạn đó phải còn hợp lý.
    Thiếu bài này thì đặt EMERGENCY_WATER_DURATION = 10**9 vẫn qua hết test."""
    assert 0 < sg.EMERGENCY_WATER_DURATION <= 300, "tưới khẩn cấp không được quá 5 phút"
    assert 0 < sg.ROOTROT_HOLD_DURATION <= 3600
    assert 0 < sg.MANUAL_OVERRIDE_DURATION <= 3600
    assert sg.AI_EMERGENCY_COOLDOWN >= sg.EMERGENCY_WATER_DURATION, (
        "cooldown phải dài hơn chính xung, nếu không sẽ tưới nối tiếp liên tục")
    assert sg.CHECK_LEAF_COOLDOWN > 0


def test_override_tay_co_thoi_han(sg, esp32):
    sg.apply_manual_command(esp32, "WATER_ON", source="test")
    with sg.state_lock:
        con_lai = sg.manual_override_until - sg.time.time()
    assert 0 < con_lai <= sg.MANUAL_OVERRIDE_DURATION


def test_lenh_auto_go_ngay_override(sg, esp32):
    sg.apply_manual_command(esp32, "WATER_ON", source="test")
    sg.apply_manual_command(esp32, "AUTO", source="test")
    with sg.state_lock:
        assert sg.manual_override_until == 0.0


def test_lenh_khong_hop_le_bi_tu_choi(sg, esp32):
    ok, msg = sg.apply_manual_command(esp32, "DROP TABLE users", source="test")
    assert ok is False
    assert "MIST_LOCK" not in esp32.da_nhan, "lệnh không thuộc tập thủ công phải bị chặn"


# ------------------------------------------------- đọc telemetry
def test_khung_su_kien_khong_ghi_de_so_lieu_cam_bien(sg, esp32, dat_cam_bien):
    """Khiếm khuyết số 11: khung watchdog từng bị đọc như khung cảm biến."""
    dat_cam_bien(soil=55, temp=29.5)
    esp32.khung = ['{"event":"watchdog","detail":"mat lien lac"}']
    sg._doc_mot_dong(esp32)
    with sg.state_lock:
        assert sg.latest_sensor.get("soil") == 55, "số liệu cảm biến phải còn nguyên"
        assert sg.latest_sensor.get("temp") == 29.5


def test_khung_hong_khong_lam_chet_luong(sg, esp32):
    for rac in ['{khong phai json', '', 'chu thuong khong phai json', '{"a":1}']:
        esp32.khung = [rac]
        sg._doc_mot_dong(esp32)      # không được ném ngoại lệ


def test_khung_hop_le_duoc_cap_nhat(sg, esp32):
    esp32.khung = ['{"temp":30.1,"humi":66,"soil":33,"light":80,'
                   '"water":"true","mist":"false","mode":"AUTO","reason":"kho"}']
    sg._doc_mot_dong(esp32)
    with sg.state_lock:
        assert sg.latest_sensor["soil"] == 33
        assert sg.last_sensor_time > 0
