"""Lớp kiểm chứng kết quả AI — normalize_ai_result().

Đây là lớp chặn giữa mô hình và bộ điều khiển. Dạng hỏng của mô hình thị giác
không phải im lặng mà là nói sai một cách tự tin, nên mọi ca ở đây đều là một
kiểu "nói sai tự tin" khác nhau.
"""
import pytest


HONG = [
    ("binh_thuong conf 0 — camera chĩa nhầm chỗ",
     {"trang_thai": "binh_thuong", "do_tin_cay": 0, "ghi_chu": "ảnh lớp học"}),
    ("mô hình tự trả khong_xac_dinh",
     {"trang_thai": "khong_xac_dinh", "do_tin_cay": 88, "ghi_chu": ""}),
    ("trạng thái ngoài enum, tiếng Anh",
     {"trang_thai": "healthy", "do_tin_cay": 95, "ghi_chu": ""}),
    ("dưới ngưỡng tin cậy",
     {"trang_thai": "heo_ru", "do_tin_cay": 30, "ghi_chu": ""}),
    ("độ tin cậy không phải số",
     {"trang_thai": "dom_nau", "do_tin_cay": "rất cao", "ghi_chu": ""}),
    ("thiếu hẳn trường trang_thai",
     {"do_tin_cay": 90, "ghi_chu": ""}),
    ("trang_thai là null",
     {"trang_thai": None, "do_tin_cay": 90, "ghi_chu": ""}),
    ("độ tin cậy âm",
     {"trang_thai": "heo_ru", "do_tin_cay": -50, "ghi_chu": ""}),
]

HOP_LE = [
    ("heo_ru 85", {"trang_thai": "heo_ru", "do_tin_cay": 85, "ghi_chu": "lá rũ"}, "heo_ru", 85),
    ("viết hoa + khoảng trắng", {"trang_thai": " DOM_NAU ", "do_tin_cay": 72, "ghi_chu": ""},
     "dom_nau", 72),
    ("đúng sát ngưỡng 40", {"trang_thai": "vang_la", "do_tin_cay": 40, "ghi_chu": ""},
     "vang_la", 40),
    ("tràn 150 phải bị kẹp về 100", {"trang_thai": "heo_ru", "do_tin_cay": 150, "ghi_chu": ""},
     "heo_ru", 100),
]


@pytest.mark.parametrize("ten,raw", HONG, ids=[t for t, _ in HONG])
def test_phan_hoi_hong_bi_loai(sg, ten, raw):
    r = sg.normalize_ai_result(raw)
    assert r["trusted"] is False, f"{ten}: đáng lẽ phải bị loại"
    assert r["trang_thai"] == "khong_xac_dinh"


@pytest.mark.parametrize("ten,raw,mong_doi,conf", HOP_LE, ids=[t for t, _, _, _ in HOP_LE])
def test_phan_hoi_hop_le_duoc_nhan(sg, ten, raw, mong_doi, conf):
    r = sg.normalize_ai_result(raw)
    assert r["trusted"] is True, f"{ten}: đáng lẽ phải được nhận"
    assert r["trang_thai"] == mong_doi
    assert r["do_tin_cay"] == conf


def test_giu_lai_trang_thai_goc_de_truy_vet(sg):
    """raw_state phải giữ nguyên chuỗi mô hình trả về, kể cả khi bị loại,
    nếu không thì không truy được vì sao chẩn đoán bị hạ cấp."""
    r = sg.normalize_ai_result({"trang_thai": "healthy", "do_tin_cay": 95})
    assert r["raw_state"] == "healthy"
    assert r["trang_thai"] == "khong_xac_dinh"


def test_ghi_chu_bi_cat_ngan(sg):
    r = sg.normalize_ai_result(
        {"trang_thai": "heo_ru", "do_tin_cay": 90, "ghi_chu": "x" * 5000})
    assert len(r["ghi_chu"]) <= 300


def test_canh_bao_camera_sau_ba_lan_lien_tiep(sg):
    for _ in range(2):
        sg.update_camera_health(sg.normalize_ai_result(
            {"trang_thai": "binh_thuong", "do_tin_cay": 0}))
    with sg.state_lock:
        assert sg.camera_alert is None, "chưa đủ 3 lần thì chưa được cảnh báo"

    sg.update_camera_health(sg.normalize_ai_result(
        {"trang_thai": "binh_thuong", "do_tin_cay": 0}))
    with sg.state_lock:
        assert sg.camera_alert is not None, "đủ 3 lần liên tiếp thì phải cảnh báo"

    sg.update_camera_health(sg.normalize_ai_result(
        {"trang_thai": "heo_ru", "do_tin_cay": 90}))
    with sg.state_lock:
        assert sg.camera_alert is None, "nhận diện lại được thì phải gỡ cảnh báo"
        assert sg.camera_blind_streak == 0
