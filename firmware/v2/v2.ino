//  Smart Home Garden - ESP32 firmware  v2.1
//
//  v2 - ban va MIST_LOCK / MIST_UNLOCK (4 thay doi):
//    1. Bien co g_mistLocked
//    2. decideMode()      - kho+nong ma bi khoa suong -> tuoi goc
//    3. readSerialCommand() - nhan MIST_LOCK / MIST_UNLOCK
//    4. printSerialJSON() - them truong "mist_locked"
//
//  v2.1 - WATCHDOG SERIAL (an toan khi Pi chet):
//    Truoc day: neu Pi gui WATER_ON roi bi mat dien / crash / bi stop, ESP32 ket
//    trong manualMode voi bom DANG CHAY va khong con ai gui lenh tat. Bom chay
//    den khi het nuoc.
//    Bay gio: Pi gui PING moi 10 giay. Neu qua SERIAL_WATCHDOG_MS ma khong nhan
//    duoc gi tu Pi VA che do thu cong nay do Pi dat ra, ESP32 tu quay ve AUTO.
//    Che do thu cong dat tu web server cua chinh ESP32 KHONG bi watchdog dung toi.
//
//  LUU Y: dung service truoc khi nap  ->  sudo systemctl stop smart-garden
// =====================================================================
#include <WiFi.h>
#include <WiFiManager.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "DHT.h"

WiFiServer server(80);
String header;
unsigned long currentTime = 0, previousTime = 0;
const long timeoutTime = 500;

#define DHTPIN       4
#define DHTTYPE      DHT11
#define LDR_PIN      34
#define SOIL_PIN     35
#define RELAY_WATER  26
#define RELAY_MIST   27
#define WIFI_RESET_PIN 0

#define SOIL_DRY_PCT_THRESHOLD 40
#define HOT_TEMP_THRESHOLD 33.0
#define DARK_LIGHT_THRESHOLD 20   // % — dưới ngưỡng này coi là tối
#define ALERT_TEMP_HIGH    38.0
#define ALERT_TEMP_LOW     10.0
#define LDR_SAMPLES        20

// NEW v2.1: Pi gui PING moi 10 giay -> 60 giay im lang = Pi da chet
#define SERIAL_WATCHDOG_MS 60000UL

Adafruit_SSD1306 display(128, 64, &Wire, -1);
DHT dht(DHTPIN, DHTTYPE);

enum IrrigationMode { MODE_IDLE, MODE_WATER, MODE_MIST };
enum MistManualMode  { MIST_OFF, MIST_ON, MIST_BLINK };

bool manualMode = false;
bool manualWater = false; 
MistManualMode manualMist = MIST_OFF;
unsigned long mistBlinkMs = 5000;

float g_temp = 0, g_humi = 0;
int   g_soilPct = 0, g_lightPct = 0, g_lightSmooth = 0;
bool  g_alertTemp = false;
String g_lastReason = "";   // NEW: hiển thị lý do quyết định lên dashboard
bool   g_mistLocked = false;  // NEW v2: Pi khoá phun sương khi AI phát hiện nấm (MIST_LOCK)
unsigned long lastSerialPrint = 0;

// NEW v2.1 — watchdog serial
unsigned long g_lastSerialMs  = 0;      // lan cuoi nhan duoc BAT KY lenh nao tu Pi
bool  g_manualFromSerial = false;       // che do thu cong hien tai do Pi dat ra?
bool  g_watchdogTripped  = false;       // da tu quay ve AUTO vi mat lien lac?

int readLDRSmoothed() {
  long sum = 0;
  for (int i = 0; i < LDR_SAMPLES; i++) { sum += analogRead(LDR_PIN); delayMicroseconds(500); }
  return sum / LDR_SAMPLES;
}

void readSensors() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t)) g_temp = t;
  if (!isnan(h)) g_humi = h;
  g_soilPct = map(analogRead(SOIL_PIN), 0, 4095, 100, 0);
  int rawLight = readLDRSmoothed();
  g_lightSmooth = (g_lightSmooth == 0) ? rawLight : (g_lightSmooth * 0.7 + rawLight * 0.3);
  g_lightPct = constrain(map(g_lightSmooth, 0, 4095, 100, 0), 0, 100);
  g_alertTemp = (g_temp > ALERT_TEMP_HIGH || g_temp < ALERT_TEMP_LOW);
}

bool getBlinkState() {
  static unsigned long timer = 0;
  static bool state = false;
  if (millis() - timer >= mistBlinkMs) { timer = millis(); state = !state; }
  return state;
}

// ── Đã thêm điều kiện isDark, có log lý do ──
IrrigationMode decideMode() {
  bool isDry  = (g_soilPct < SOIL_DRY_PCT_THRESHOLD);
  bool isHot  = (g_temp >= HOT_TEMP_THRESHOLD);
  bool isDark = (g_lightPct < DARK_LIGHT_THRESHOLD);

  if (isDark && isDry) { g_lastReason = "Toi + kho - tranh ung"; return MODE_IDLE; }

  if (isDry && isHot) {
    if (g_mistLocked) {                                    // NEW v2
      g_lastReason = "Kho + nong nhung SUONG BI KHOA (nam) - tuoi goc";
      return MODE_WATER;
    }
    g_lastReason = "Kho + nong - phun suong";
    return MODE_MIST;
  }

  if (isDry && !isHot) { g_lastReason = "Kho + binh thuong - tuoi goc"; return MODE_WATER; }

  g_lastReason = g_mistLocked ? "Dat du am - nghi (suong dang khoa)" : "Dat du am - nghi";
  return MODE_IDLE;
}

void applyMode() {
  bool waterOn = false, mistOn = false;

  if (manualMode) {
    waterOn = manualWater;
    switch (manualMist) {
      case MIST_OFF:   mistOn = false; break;
      case MIST_ON:    mistOn = true;  break;
      case MIST_BLINK: mistOn = getBlinkState(); break;
    }
    if (waterOn) mistOn = false;
    g_lastReason = "Che do thu cong";
  } else {
    IrrigationMode m = decideMode();
    waterOn = (m == MODE_WATER);
    mistOn  = (m == MODE_MIST) ? getBlinkState() : false;
  }

  digitalWrite(RELAY_WATER, waterOn ? LOW : HIGH);
  digitalWrite(RELAY_MIST,  mistOn  ? LOW : HIGH);
}

bool isWaterOn() { return digitalRead(RELAY_WATER) == LOW; }
bool isMistOn()  { return digitalRead(RELAY_MIST)  == LOW; }

void updateOLED() {
  static bool page = false;
  static unsigned long lastPage = 0;
  if (millis() - lastPage > 3000) { page = !page; lastPage = millis(); }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("== Smart Garden ==");

  if (!page) {
    display.setCursor(0, 12);
    display.print("T:"); display.print(g_temp, 1);
    display.print("C H:"); display.print(g_humi, 0); display.println("%");
    display.setCursor(0, 22);
    display.print("Dat:"); display.print(g_soilPct); display.print("% ");
    display.print("Sang:"); display.println(g_lightPct);
    display.setCursor(0, 34);
    display.print("Mode: "); display.println(manualMode ? "MANUAL" : "AUTO");
    if (WiFi.status() == WL_CONNECTED) {
      display.setCursor(0, 46);
      display.print("IP:"); display.println(WiFi.localIP());
    } else {
      display.setCursor(0, 46);
      display.println("Giu BOOT 3s: doi WiFi");
    }
  } else {
    display.setCursor(0, 14);
    display.print("Tuoi goc: "); display.println(isWaterOn() ? "ON" : "OFF");
    display.setCursor(0, 26);
    display.print("Phun suong:"); display.println(isMistOn() ? "ON" : "OFF");
    if (g_alertTemp) { display.setCursor(0, 44); display.println("! NHIET DO BAT THUONG !"); }
  }
  display.display();
}

void handleWebClient() {
  WiFiClient client = server.available();
  if (!client) return;

  currentTime = millis();
  previousTime = currentTime;
  String currentLine = "";

  while (client.connected() && currentTime - previousTime <= timeoutTime) {
    currentTime = millis();
    if (client.available()) {
      char c = client.read();
      header += c;
      if (c == '\n') {
        if (currentLine.length() == 0) {

          // NEW v2.1: che do thu cong dat tu web UI cua ESP32 KHONG thuoc quyen Pi,
          // nen watchdog serial khong duoc phep tu y huy no.
          if (header.indexOf("GET /mode/auto")   >= 0) { manualMode = false; g_manualFromSerial = false; }
          if (header.indexOf("GET /mode/manual") >= 0) { manualMode = true;  g_manualFromSerial = false; }
          if (header.indexOf("GET /water/on")    >= 0) manualWater = true;
          if (header.indexOf("GET /water/off")   >= 0) manualWater = false;
          if (header.indexOf("GET /mist/off")    >= 0) manualMist = MIST_OFF;
          if (header.indexOf("GET /mist/on")     >= 0) manualMist = MIST_ON;
          if (header.indexOf("GET /mist/blink")  >= 0) manualMist = MIST_BLINK;

          int idx = header.indexOf("val=");
          if (idx >= 0 && header.indexOf("GET /mist/interval") >= 0) {
            int start = idx + 4;
            int end = start;
            while (end < (int)header.length() && isDigit(header[end])) end++;
            long val = header.substring(start, end).toInt();
            if (val >= 500 && val <= 60000) mistBlinkMs = val;
          }
          applyMode();

          client.println("HTTP/1.1 200 OK");
          client.println("Content-type:text/html; charset=utf-8");
          client.println("Connection: close");
          client.println();

          bool wOn = isWaterOn(), mOn = isMistOn();

          client.println("<!DOCTYPE html><html><head>");
          client.println("<meta charset='UTF-8'>");
          client.println("<meta http-equiv='refresh' content='5'>");
          client.println("<meta name='viewport' content='width=device-width, initial-scale=1'>");
          client.println("<title>Smart Garden</title><style>");
          client.println("*{box-sizing:border-box;margin:0;padding:0;}");
          client.println("body{font-family:-apple-system,'Segoe UI',Arial,sans-serif;background:#f4f4f5;color:#1c1c1e;padding:16px;}");
          client.println(".wrap{max-width:460px;margin:0 auto;}");
          client.println("h2{text-align:center;font-size:20px;font-weight:600;margin-bottom:16px;}");
          client.println(".card{background:#fff;border:1px solid #e2e2e5;border-radius:12px;padding:16px;margin-bottom:14px;}");
          client.println(".grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;}");
          client.println(".stat{text-align:center;padding:14px 8px;background:#f8f8f9;border-radius:10px;}");
          client.println(".stat .val{font-size:22px;font-weight:700;}");
          client.println(".stat .lbl{font-size:11px;color:#777;margin-top:2px;}");
          client.println(".row{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;font-size:14px;}");
          client.println(".badge{padding:3px 10px;border-radius:6px;font-size:12px;font-weight:600;}");
          client.println(".badge.on{background:#e6f4ea;color:#1a7f37;}");
          client.println(".badge.off{background:#eee;color:#888;}");
          client.println(".btnrow{display:flex;gap:8px;flex-wrap:wrap;}");
          client.println(".btn{flex:1;min-width:80px;text-align:center;padding:12px 10px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;border:1px solid #d7d7db;color:#333;background:#fafafa;}");
          client.println(".btn.active{background:#1c1c1e;color:#fff;border-color:#1c1c1e;}");
          client.println(".disabled{opacity:0.4;pointer-events:none;}");
          client.println("hr{border:none;border-top:1px solid #eee;margin:14px 0;}");
          client.println("input[type=number]{width:64px;padding:8px;border-radius:8px;border:1px solid #d7d7db;margin-right:6px;font-size:13px;}");
          client.println(".apply{padding:8px 14px;border-radius:8px;border:1px solid #d7d7db;background:#fafafa;font-size:13px;font-weight:600;}");
          client.println(".alert{background:#fdecea;border:1px solid #f5b3ab;color:#a33;padding:10px;border-radius:10px;text-align:center;font-weight:600;margin-bottom:14px;font-size:13px;}");
          client.println(".reason{background:#f0f4ff;border:1px solid #c8d6ff;color:#2a4b8d;padding:8px 12px;border-radius:8px;font-size:12px;margin-bottom:14px;}");
          client.println(".footer{text-align:center;font-size:11px;color:#999;margin-top:8px;}");
          client.println("</style></head><body><div class='wrap'>");
          client.println("<h2>Smart Garden - SIC</h2>");

          if (g_alertTemp)
            client.println("<div class='alert'>Canh bao: nhiet do bat thuong (" + String(g_temp,1) + " do C)</div>");

          client.println("<div class='reason'>Ly do: " + g_lastReason + "</div>");

          client.println("<div class='card'><div class='grid'>");
          client.println("<div class='stat'><div class='val'>" + String(g_temp,1) + "&deg;</div><div class='lbl'>NHIET DO</div></div>");
          client.println("<div class='stat'><div class='val'>" + String(g_humi,0) + "%</div><div class='lbl'>DO AM KK</div></div>");
          client.println("<div class='stat'><div class='val'>" + String(g_soilPct) + "%</div><div class='lbl'>DO AM DAT</div></div>");
          client.println("<div class='stat'><div class='val'>" + String(g_lightPct) + "%</div><div class='lbl'>ANH SANG</div></div>");
          client.println("</div></div>");

          client.println("<div class='card'>");
          client.println("<div class='row'><b>Che do</b></div>");
          client.println("<div class='btnrow'>");
          client.println("<a href='/mode/auto' class='btn" + String(!manualMode ? " active" : "") + "'>AUTO</a>");
          client.println("<a href='/mode/manual' class='btn" + String(manualMode ? " active" : "") + "'>MANUAL</a>");
          client.println("</div></div>");

          String dis = manualMode ? "" : " disabled";
          client.println("<div class='card" + dis + "'>");
          client.println("<div class='row'><span>Bom tuoi goc</span>" + String(wOn ? "<span class='badge on'>ON</span>" : "<span class='badge off'>OFF</span>") + "</div>");
          client.println("<div class='btnrow'>");
          client.println(wOn ? "<a href='/water/off' class='btn active'>TAT TUOI</a>"
                              : "<a href='/water/on' class='btn'>BAT TUOI</a>");
          client.println("</div>");
          client.println("<hr>");
          client.println("<div class='row'><span>Bom phun suong</span>" + String(mOn ? "<span class='badge on'>ON</span>" : "<span class='badge off'>OFF</span>") + "</div>");
          client.println("<div class='btnrow'>");
          client.println("<a href='/mist/off' class='btn" + String(manualMist==MIST_OFF?" active":"") + "'>TAT</a>");
          client.println("<a href='/mist/on' class='btn" + String(manualMist==MIST_ON?" active":"") + "'>LIEN TUC</a>");
          client.println("<a href='/mist/blink' class='btn" + String(manualMist==MIST_BLINK?" active":"") + "'>NHAP NHAY</a>");
          client.println("</div>");
          client.println("<div style='margin-top:12px;font-size:12px;color:#777'>Chu ky nhap nhay (giay):</div>");
          client.println("<form action='/mist/interval' method='GET' style='margin-top:6px;display:flex;align-items:center;'>");
          client.println("<input type='number' id='vd' step='0.5' min='0.5' max='60' value='" + String(mistBlinkMs/1000.0,1) + "' onchange=\"document.getElementById('val').value=Math.round(this.value*1000)\">");
          client.println("<input type='hidden' name='val' id='val' value='" + String(mistBlinkMs) + "'>");
          client.println("<button type='submit' class='apply'>Ap dung</button>");
          client.println("</form></div>");

          client.println("<div class='footer'>Tu lam moi moi 5 giay - ESP32 Smart Garden</div>");
          client.println("</div></body></html>");
          client.println();
          break;
        } else { currentLine = ""; }
      } else if (c != '\r') { currentLine += c; }
    }
  }
  header = "";
  client.stop();
}

void connectWiFi() {
  WiFiManager wm;
  wm.setConfigPortalTimeout(180);
  bool ok = wm.autoConnect("SmartGarden-Setup", "12345678");
  if (!ok) {
    Serial.println("[WiFi] Khong ket noi duoc / het thoi gian cho cau hinh.");
  } else {
    Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
    server.begin();
  }
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(RELAY_WATER, OUTPUT);
  pinMode(RELAY_MIST,  OUTPUT);
  pinMode(WIFI_RESET_PIN, INPUT_PULLUP);
  digitalWrite(RELAY_WATER, HIGH);
  digitalWrite(RELAY_MIST,  HIGH);

  Wire.begin(21, 22);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(10, 25);
  display.println("Dang khoi dong...");
  display.display();

  if (digitalRead(WIFI_RESET_PIN) == LOW) {
    display.setCursor(0, 40);
    display.println("Xoa WiFi cu...");
    display.display();
    WiFiManager wmReset;
    wmReset.resetSettings();
    delay(1000);
  }

  connectWiFi();

  display.clearDisplay();
  display.setCursor(0, 20);
  if (WiFi.status() == WL_CONNECTED) { display.println("IP:"); display.println(WiFi.localIP()); }
  else {
    display.println("Chua co WiFi.");
    display.println("Ket noi mang:");
    display.println("SmartGarden-Setup");
  }
  display.display();
  delay(2000);
}
void printSerialJSON() {
  if (millis() - lastSerialPrint < 2000) return;  // in mỗi 2 giây, không spam
  lastSerialPrint = millis();
  Serial.printf(
    "{\"temp\":%.1f,\"humi\":%.0f,\"soil\":%d,\"light\":%d,\"water\":%s,\"mist\":%s,"
    "\"mist_locked\":%s,\"wd_tripped\":%s,\"mode\":\"%s\",\"reason\":\"%s\"}\n",
    g_temp, g_humi, g_soilPct, g_lightPct,
    isWaterOn() ? "true" : "false",
    isMistOn()  ? "true" : "false",
    g_mistLocked ? "true" : "false",     // NEW v2
    g_watchdogTripped ? "true" : "false",  // NEW v2.1
    manualMode ? "MANUAL" : "AUTO",
    g_lastReason.c_str()
  );
}
void readSerialCommand() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.length() == 0) return;

  // NEW v2.1: bat ky dong nao tu Pi cung la bang chung "Pi con song"
  g_lastSerialMs   = millis();
  g_watchdogTripped = false;

  if (cmd == "PING") return;   // chi de nuoi watchdog, khong doi trang thai

  if (cmd == "WATER_ON")   { manualMode = true; manualWater = true;  g_manualFromSerial = true; }
  if (cmd == "WATER_OFF")  { manualMode = true; manualWater = false; g_manualFromSerial = true; }
  if (cmd == "MIST_ON")    { manualMode = true; manualMist = MIST_ON;  g_manualFromSerial = true; }
  if (cmd == "MIST_OFF")   { manualMode = true; manualMist = MIST_OFF; g_manualFromSerial = true; }
  if (cmd == "AUTO")       { manualMode = false; g_manualFromSerial = false; }
  // THÊM: khóa cứng tắt hết, không để AUTO quyết định
  if (cmd == "LOCK_IDLE")  {
    manualMode  = true;
    manualWater = false;
    manualMist  = MIST_OFF;
    g_manualFromSerial = true;
  }
  // NEW v2: khoá riêng phun sương, KHÔNG chuyển sang manualMode
  // -> ESP32 vẫn tự quyết tưới gốc theo ngưỡng độ ẩm đất
  if (cmd == "MIST_LOCK")   { g_mistLocked = true;  }
  if (cmd == "MIST_UNLOCK") { g_mistLocked = false; }

  applyMode();
}

// NEW v2.1 — Pi im lang qua lau thi tu cuu lay minh.
// Chi can thiep vao che do thu cong DO PI DAT RA. Neu nguoi dung bam MANUAL tren
// web server cua ESP32 thi g_manualFromSerial = false, watchdog khong dung toi.
void checkSerialWatchdog() {
  if (!g_manualFromSerial) return;
  if (g_lastSerialMs == 0) return;                       // chua tung nhan lenh nao
  if (millis() - g_lastSerialMs < SERIAL_WATCHDOG_MS) return;

  manualMode         = false;
  manualWater        = false;
  manualMist         = MIST_OFF;
  g_mistLocked       = false;   // khoa suong cung la lenh cua Pi -> bo luon
  g_manualFromSerial = false;
  g_watchdogTripped  = true;
  g_lastReason = "WATCHDOG: mat lien lac voi Pi - tu quay ve AUTO";
  Serial.println("{\"event\":\"watchdog\",\"detail\":\"mat lien lac voi Pi, da ve AUTO\"}");
  applyMode();
}

void loop() {
  readSensors();
  checkSerialWatchdog();
  applyMode();
  updateOLED();
  handleWebClient();
  printSerialJSON();
  readSerialCommand();
}
