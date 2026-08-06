#!/usr/bin/env bash
#
# Smart Home Garden — Cài đặt tự động trên Raspberry Pi 5 (Raspberry Pi OS Bookworm)
#
#   Cách dùng:  cd ~/smart_garden && bash deploy/install.sh
#
# Script này KHÔNG ghi đè GEMINI_API_KEY nếu bạn đã cấu hình trước đó.
#
set -euo pipefail

APP_USER="${SUDO_USER:-$USER}"
APP_DIR="/home/${APP_USER}/smart_garden"
ENV_FILE="/etc/smart-garden.env"
SERVICE="smart-garden.service"

c_g() { printf '\033[92m%s\033[0m\n' "$*"; }
c_y() { printf '\033[93m%s\033[0m\n' "$*"; }
c_r() { printf '\033[91m%s\033[0m\n' "$*"; }
step() { printf '\n\033[96m\033[1m==> %s\033[0m\n' "$*"; }

if [[ "$(id -u)" -eq 0 && -z "${SUDO_USER:-}" ]]; then
  c_r "Đừng chạy trực tiếp bằng root. Hãy chạy: bash deploy/install.sh (script tự gọi sudo khi cần)."
  exit 1
fi

step "1/8 · Kiểm tra môi trường"
echo "Người dùng : ${APP_USER}"
echo "Thư mục    : ${APP_DIR}"
echo "Kiến trúc  : $(uname -m)"
[[ -f /proc/device-tree/model ]] && echo "Thiết bị   : $(tr -d '\0' < /proc/device-tree/model)"

if [[ ! -f "${APP_DIR}/main.py" ]]; then
  c_r "Không tìm thấy ${APP_DIR}/main.py — hãy copy toàn bộ thư mục dự án vào ${APP_DIR} trước."
  exit 1
fi

step "2/8 · Cài gói hệ thống"
sudo apt-get update -qq
sudo apt-get install -y \
  python3-venv python3-pip python3-dev \
  libgl1 libglib2.0-0 libatlas-base-dev \
  v4l-utils sqlite3 git

step "3/8 · Cấp quyền cổng serial và camera"
sudo usermod -aG dialout,video "${APP_USER}"
c_y "Đã thêm ${APP_USER} vào nhóm dialout + video (cần đăng xuất/đăng nhập lại mới có hiệu lực ở shell)."

# Tên cổng USB có thể đổi giữa ttyUSB0/ttyUSB1 sau mỗi lần cắm lại.
# Tạo symlink cố định /dev/esp32 dựa theo chip UART (CP2102 hoặc CH340).
step "4/8 · Tạo tên cổng cố định /dev/esp32"
sudo tee /etc/udev/rules.d/99-smart-garden.rules >/dev/null <<'RULE'
# CP2102 (Silicon Labs) — phổ biến trên ESP32 DevKit V1
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="esp32", MODE="0660", GROUP="dialout"
# CH340 / CH341 (WCH) — hay gặp trên board giá rẻ
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="esp32", MODE="0660", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d4", SYMLINK+="esp32", MODE="0660", GROUP="dialout"
RULE
sudo udevadm control --reload-rules
sudo udevadm trigger || true
sleep 2
if [[ -e /dev/esp32 ]]; then
  c_g "✅ /dev/esp32 -> $(readlink -f /dev/esp32)"
else
  c_y "⚠️  Chưa thấy /dev/esp32. Rút và cắm lại cáp USB của ESP32 rồi kiểm tra: ls -l /dev/esp32"
fi

step "5/8 · Tạo virtualenv và cài thư viện Python"
cd "${APP_DIR}"
[[ -d venv ]] || python3 -m venv venv
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -q \
  flask \
  pyserial \
  opencv-python-headless \
  google-genai
c_g "✅ Đã cài xong thư viện."
./venv/bin/python -c "import flask,serial,cv2,google.genai; print('   flask+pyserial+opencv+genai OK')"

step "6/8 · Tạo file biến môi trường ${ENV_FILE}"
if [[ -f "${ENV_FILE}" ]] && sudo grep -q 'GEMINI_API_KEY=..' "${ENV_FILE}"; then
  c_y "Đã tồn tại ${ENV_FILE} và có sẵn API key — giữ nguyên, không ghi đè."
else
  read -rp "Nhập GEMINI_API_KEY (lấy tại https://aistudio.google.com/apikey): " GKEY
  sudo tee "${ENV_FILE}" >/dev/null <<EOF
GEMINI_API_KEY=${GKEY}
SG_SERIAL_PORT=/dev/esp32
SG_CAM_INDEX=0
SG_PORT=5000
SG_MODEL=gemini-3.1-flash-lite
EOF
  sudo chown root:root "${ENV_FILE}"
  sudo chmod 600 "${ENV_FILE}"
  c_g "✅ Đã tạo ${ENV_FILE} (chmod 600 — chỉ root đọc được, API key không lộ)."
fi

step "7/8 · Cài systemd service"
sudo sed -e "s|/home/pi/smart_garden|${APP_DIR}|g" \
         -e "s|^User=pi$|User=${APP_USER}|" \
         -e "s|^Group=pi$|Group=${APP_USER}|" \
         "${APP_DIR}/deploy/${SERVICE}" | sudo tee "/etc/systemd/system/${SERVICE}" >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE}"
c_g "✅ Đã bật khởi động cùng hệ thống."

step "8/8 · Khởi động dịch vụ"
mkdir -p "${APP_DIR}/photos"
sudo systemctl restart "${SERVICE}"
sleep 6
sudo systemctl --no-pager --lines=15 status "${SERVICE}" || true

IP=$(hostname -I | awk '{print $1}')
cat <<EOF

$(c_g "════════════════════════════════════════════════════════")
$(c_g "  CÀI ĐẶT HOÀN TẤT")
$(c_g "════════════════════════════════════════════════════════")

  Dashboard   : http://${IP}:5000
  Xem log     : sudo journalctl -u ${SERVICE} -f
  Khởi động lại: sudo systemctl restart ${SERVICE}
  Dừng        : sudo systemctl stop ${SERVICE}
  Cơ sở dữ liệu: sqlite3 ${APP_DIR}/smart_garden.db

  $(c_y "Bước tiếp theo bắt buộc:")
  1. Chĩa camera vào khay rau, bấm "Chụp & chẩn đoán ngay" trên dashboard
     và xác nhận nhãn "ĐỦ TIN CẬY" hiện lên (sửa Blocker 1).
  2. Nạp firmware ESP32 (firmware/v2/v2.ino) để lệnh MIST_LOCK
     và watchdog serial hoạt động — không nạp thì hệ thống vẫn chạy, chỉ mất
     tính năng cấm phun sương khi phát hiện đốm nâu.

EOF
