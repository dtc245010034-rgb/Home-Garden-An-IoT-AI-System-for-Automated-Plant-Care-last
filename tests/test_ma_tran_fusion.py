"""Ma trận fusion AI x độ ẩm đất — quét đủ mọi ô.

Đây là phần trả lời câu hỏi "làm sao test khi điều kiện thật không xảy ra":
trạng thái AI và độ ẩm đất đều chỉ là dữ liệu trong bộ nhớ, dựng lại được hết.
"""
import pytest

KHO = 25        # dưới ngưỡng 40
AM = 75         # trên ngưỡng 40


def _quyet_dinh(sg, dat_ai, dat_cam_bien, trang_thai, conf, soil, tuoi=0.0):
    dat_cam_bien(soil=soil, tuoi=tuoi)
    if trang_thai:
        dat_ai(trang_thai, conf, soil)
    khan = sg.check_ai_emergency()
    if khan:
        return khan
    return sg.decide_fusion()


# ---------------------------------------------------------------- mức 1
def test_heo_ru_dat_kho_thi_tuoi_xung(sg, dat_ai, dat_cam_bien):
    cmds, ly_do, muc = _quyet_dinh(sg, dat_ai, dat_cam_bien, "heo_ru", 95, KHO)
    assert cmds == ["WATER_ON"]
    assert muc.startswith("1")
    assert sg.pulse_remaining("emergency_water") > 0


def test_heo_ru_dat_am_thi_KHOA_chu_khong_tuoi(sg, dat_ai, dat_cam_bien):
    """Ô quyết định nhất của cả đồ án: cùng triệu chứng, hành vi ngược lại."""
    cmds, ly_do, muc = _quyet_dinh(sg, dat_ai, dat_cam_bien, "heo_ru", 95, AM)
    assert cmds == ["LOCK_IDLE"], "đất còn ẩm mà héo rũ là nghi thối rễ, cấm tưới"
    assert "WATER_ON" not in cmds
    assert muc.startswith("1")
    assert sg.pulse_remaining("rootrot_hold") > 0


def test_mat_so_lieu_dat_thi_van_tuoi_khan_cap(sg, dat_ai, dat_cam_bien):
    """Không có số liệu đất thì phải nghiêng về cứu cây, nhưng vẫn có thời hạn."""
    dat_cam_bien(soil=None, tuoi=0)
    dat_ai("heo_ru", 95)
    cmds, ly_do, muc = sg.check_ai_emergency()
    assert cmds == ["WATER_ON"]
    assert "không có số liệu đất" in ly_do


def test_so_lieu_dat_qua_cu_coi_nhu_mat(sg, dat_ai, dat_cam_bien):
    dat_cam_bien(soil=AM, tuoi=sg.SENSOR_STALE_SEC + 5)
    soil, kho, moi = sg.read_soil_state()
    assert moi is False, "số liệu quá SENSOR_STALE_SEC phải bị coi là mất"


def test_heo_ru_duoi_nguong_khan_cap_khong_kich_hoat_muc_1(sg, dat_ai, dat_cam_bien):
    dat_cam_bien(soil=KHO)
    dat_ai("heo_ru", 65)          # >= AI_MIN_CONF nhưng < AI_EMERGENCY_CONF
    assert sg.check_ai_emergency() is None
    cmds, ly_do, muc = sg.decide_fusion()
    assert muc.startswith("4")
    assert "WATER_ON" not in cmds


# ---------------------------------------------------------------- mức 4
def test_dom_nau_cam_phun_suong_ca_hai_muc_do_am(sg, dat_ai, dat_cam_bien):
    for soil in (KHO, AM):
        sg.pulse_state.clear()
        cmds, ly_do, muc = _quyet_dinh(sg, dat_ai, dat_cam_bien, "dom_nau", 80, soil)
        assert "MIST_LOCK" in cmds, f"đất {soil}%: nấm gặp ẩm sẽ lan, phải cấm sương"
        assert "AUTO" in cmds, "vẫn phải cho tưới gốc theo ngưỡng"


def test_vang_la_dat_am_la_thieu_dam_khong_tuoi_them(sg, dat_ai, dat_cam_bien):
    cmds, ly_do, muc = _quyet_dinh(sg, dat_ai, dat_cam_bien, "vang_la", 80, AM)
    assert "WATER_ON" not in cmds
    assert "ĐẠM" in ly_do.upper()


def test_binh_thuong_thi_mo_khoa_suong(sg, dat_ai, dat_cam_bien):
    cmds, ly_do, muc = _quyet_dinh(sg, dat_ai, dat_cam_bien, "binh_thuong", 90, AM)
    assert cmds == ["MIST_UNLOCK", "AUTO"]


@pytest.mark.parametrize("trang_thai,conf", [
    ("binh_thuong", 0),      # không đáng tin
    ("healthy", 95),         # ngoài enum
    ("heo_ru", 20),          # dưới ngưỡng
])
def test_chan_doan_khong_dang_tin_khong_duoc_dong_vao_actuator(
        sg, dat_ai, dat_cam_bien, trang_thai, conf):
    """Bất kể AI nói gì, không đáng tin thì hệ phải chạy thuần cảm biến."""
    cmds, ly_do, muc = _quyet_dinh(sg, dat_ai, dat_cam_bien, trang_thai, conf, KHO)
    assert cmds == ["MIST_UNLOCK", "AUTO"]
    assert muc.startswith("5"), "phải rơi về mức mặc định"


def test_chua_co_chan_doan_nao_van_chay_duoc(sg, dat_cam_bien):
    dat_cam_bien(soil=KHO)
    cmds, ly_do, muc = sg.decide_fusion()
    assert cmds == ["MIST_UNLOCK", "AUTO"]


# ---------------------------------------------------------------- bảng tổng
def test_dung_ba_o_doi_hanh_vi_co_cau_chap_hanh(sg, dat_ai, dat_cam_bien):
    """Báo cáo tuyên bố 'ít nhất ba ô khác với hệ chỉ dùng cảm biến'.
    Bài này kiểm chứng đúng con số đó."""
    o_doi_hanh_vi = []
    for trang_thai, conf in [("heo_ru", 95), ("dom_nau", 80), ("vang_la", 80),
                             ("binh_thuong", 90)]:
        for soil in (KHO, AM):
            sg.pulse_state.clear()
            cmds, _, _ = _quyet_dinh(sg, dat_ai, dat_cam_bien, trang_thai, conf, soil)
            # "khác hệ chỉ dùng cảm biến" = có lệnh ép, không phải AUTO thuần
            if any(c in cmds for c in ("WATER_ON", "LOCK_IDLE", "MIST_LOCK")):
                o_doi_hanh_vi.append((trang_thai, soil))
    assert len(o_doi_hanh_vi) == 4, o_doi_hanh_vi
    # heo_ru kho, heo_ru am, dom_nau kho, dom_nau am
    assert ("heo_ru", KHO) in o_doi_hanh_vi
    assert ("heo_ru", AM) in o_doi_hanh_vi
