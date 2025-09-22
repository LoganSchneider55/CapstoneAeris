#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <sys/time.h>
#include <time.h>
#include "esp_heap_caps.h"   // for MALLOC_CAP_SPIRAM

// ---------- Wi-Fi ----------
const char* WIFI_SSID = "Cesar iPhone";
const char* WIFI_PASS = "Yuca12345";

// ---------- API (Render) ----------
const char* API_BASE = "https://capstoneaerisapi.onrender.com";
const char* PATH_DEVICES  = "/v1/devices";
const char* PATH_READINGS = "/v1/readings";
const char* API_KEY = "TEST_KEY_123";

// Sensor-type labels expected by backend
const char* SENSOR_TEMP = "temperature_c";
const char* SENSOR_HUM  = "humidity";
const char* SENSOR_PRES = "pressure_hpa";

// ---------- BME280 ----------
Adafruit_BME280 bme;
bool bme_ok = false;

// ---------- Timing ----------
unsigned long lastSample = 0;
const unsigned long SAMPLE_MS = 2000;

// ---------- Identity ----------
String device_id;

// ================= PSRAM Ring Buffer for Offline Readings =================
struct Reading {
  char sensor_type[32]; // "temperature_c", etc.
  float value; // reading value
  char measured_at[32]; // ISO-8601 UTC ms, e.g. 2025-09-16T00:00:00.123Z
};

static Reading* rb = nullptr; // circular buffer
static size_t   rb_cap = 0;
static size_t   rb_head = 0; // next write
static size_t   rb_tail = 0; // next read
static bool     rb_overwrite_on_full = true; // enables circular behavior

// 1024 * sizeof(Reading) ~ ~64KB, PSRAM has 2 MB of memory, so this can be increased in the future
#ifndef RB_CAPACITY
#define RB_CAPACITY 1024
#endif

bool rbInit(size_t capacity) {
  rb = (Reading*) heap_caps_malloc(sizeof(Reading) * capacity, MALLOC_CAP_SPIRAM);
  if (!rb) return false;
  rb_cap = capacity;
  rb_head = rb_tail = 0;
  return true;
}

inline bool rbEmpty() {
  return rb_head == rb_tail;
}

inline bool rbFull() {
  return ((rb_head + 1) % rb_cap) == rb_tail;
}

void rbPush(const char* sensor_type, float value, const String& measured_at) {
  if (!rb) return;
  if (rbFull()) {
    if (rb_overwrite_on_full) {
      // Drop oldest
      rb_tail = (rb_tail + 1) % rb_cap;
    }
    else {
      // Refuse push
      return;
    }
  }
  // Write at head
  Reading& r = rb[rb_head];
  // Safe copies
  strncpy(r.sensor_type, sensor_type, sizeof(r.sensor_type) - 1);
  r.sensor_type[sizeof(r.sensor_type) - 1] = '\0';
  r.value = value;
  measured_at.toCharArray(r.measured_at, sizeof(r.measured_at));
  // Advance head
  rb_head = (rb_head + 1) % rb_cap;
}

bool rbPop(Reading& out) {
  if (!rb || rbEmpty()) return false;
  out = rb[rb_tail];
  rb_tail = (rb_tail + 1) % rb_cap;
  return true;
}

size_t rbSize() {
  if (rb_head >= rb_tail) return rb_head - rb_tail;
  return rb_cap - (rb_tail - rb_head);
}

// ---------------- Time: ISO-8601 UTC with milliseconds ----------------
void setupTimeUTC() {
  configTzTime("UTC0", "pool.ntp.org", "time.nist.gov");
  struct tm t;
  for (int i = 0; i < 50; ++i) {      // ~10s max
    if (getLocalTime(&t, 200)) return;
    delay(200);
  }
  Serial.println("[TIME] NTP sync failed (continuing).");
}

String iso8601_utc_ms() {
  struct timeval tv;
  gettimeofday(&tv, nullptr); // UTC
  time_t sec = tv.tv_sec;
  struct tm tm_utc;
  gmtime_r(&sec, &tm_utc);
  char base[32];
  strftime(base, sizeof(base), "%Y-%m-%dT%H:%M:%S", &tm_utc);
  char out[40];
  snprintf(out, sizeof(out), "%s.%03ldZ", base, tv.tv_usec / 1000);
  return String(out);
}

// ---------------- Wi-Fi ----------------
bool ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to WiFi");
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 20000) {
    delay(400);
    Serial.print(".");
  }
  Serial.println(WiFi.status()==WL_CONNECTED ? "\nConnected!" : "\nWiFi timeout");
  if (WiFi.status()==WL_CONNECTED) {
    Serial.print("IP: "); Serial.println(WiFi.localIP());
    return true;
  }
  return false;
}

// ---------------- HTTP helper ----------------
bool httpPostJson(const String& url, const String& json, int& code_out, String& resp_out) {
  if (WiFi.status() != WL_CONNECTED) { // quick fail if offline
    code_out = -2;
    resp_out = "offline";
    return false;
  }

  WiFiClientSecure client;
  client.setInsecure(); // OK for bring-up; load a CA for production

  HTTPClient http;
  http.setTimeout(15000); // Render free tier can cold-start
  if (!http.begin(client, url)) {
    Serial.println("[HTTP] begin() failed");
    code_out = -1;
    return false;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", String("Bearer ") + API_KEY);

  code_out = http.POST(json);
  resp_out = http.getString();
  Serial.print("[HTTP] "); Serial.print(url);
  Serial.print(" -> "); Serial.print(code_out);
  Serial.print(" | resp: "); Serial.println(resp_out);
  http.end();
  return (code_out >= 200 && code_out < 300) || code_out == 409; // 409 = already exists
}

// ---------------- API calls ----------------
bool registerDevice() {
  String url = String(API_BASE) + PATH_DEVICES;
  String body = String("{") +
    "\"device_id\":\"" + device_id + "\"," +
    "\"name\":\"AERIS ESP32-S2\"," +
    "\"location\":\"bench\"" +
  "}";
  int code; String resp;
  bool ok = httpPostJson(url, body, code, resp);
  if (!ok) Serial.println("[DEV] registration failed.");
  return ok;
}

bool sendReadingJson(const char* sensor_type, float value, const String& ts) {
  String url = String(API_BASE) + PATH_READINGS;

  String body = String("{") +
    "\"device_id\":\"" + device_id + "\"," +
    "\"sensor_type\":\"" + sensor_type + "\"," +
    "\"measured_at\":\"" + ts + "\"," +
    "\"value\":" + String(value, 2) +
  "}";

  int code; String resp;
  bool ok = httpPostJson(url, body, code, resp);
  if (code == 401) Serial.println("[API] 401: check API_KEY.");
  if (code == 422) Serial.println("[API] 422: schema mismatch (sensor_type or timestamp format).");
  return ok;
}

// Overload that takes a buffered Reading
bool sendReading(const Reading& r) {
  return sendReadingJson(r.sensor_type, r.value, String(r.measured_at));
}

// Try to flush up to N buffered readings this loop
void flushBufferedReadings(size_t max_to_flush = 10) {
  if (WiFi.status() != WL_CONNECTED) return;
  size_t flushed = 0;
  Reading r;
  while (flushed < max_to_flush && rbPop(r)) {
    if (!sendReading(r)) {
      // Sending failed (server hiccup or temporary issue). Put it back and stop.
      rb_tail = (rb_tail == 0 ? rb_cap - 1 : rb_tail - 1);
      Serial.println("[BUF] Flush paused due to send failure.");
      break;
    }
    flushed++;
  }
  if (flushed > 0) {
    Serial.print("[BUF] Flushed "); Serial.print(flushed);
    Serial.print(" / "); Serial.print(rbSize()); Serial.println(" pending.");
  }
}

// ---------------- Setup / Loop ----------------
void setup() {
  Serial.begin(115200);
  delay(100);

  device_id = "esp32";

  // Initialize PSRAM-backed buffer
  if (ESP.getPsramSize() == 0) {
    Serial.println("[PSRAM] Not found! Buffering will use internal heap and may be limited.");
  }
  if (!rbInit(RB_CAPACITY)) {
    Serial.println("[PSRAM] Allocation failed; falling back to no buffering.");
  }
  else {
    Serial.print("[PSRAM] Ring buffer ready, capacity="); Serial.println(RB_CAPACITY);
  }

  // Sensor
  Wire.begin();
  bme_ok = bme.begin(0x76);
  if (!bme_ok) bme_ok = bme.begin(0x77);
  Serial.println(bme_ok ? "BME280 found ✅" : "BME280 not found ❌");

  ensureWiFi();
  setupTimeUTC();
  registerDevice();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    ensureWiFi();
  }

  // If connected, always try to drain some of the backlog
  flushBufferedReadings(15); // tune this up/down based on CPU/time budget

  unsigned long now = millis();
  if (now - lastSample >= SAMPLE_MS) {
    lastSample = now;

    if (bme_ok) {
      float t = bme.readTemperature();        // °C
      float h = bme.readHumidity();           // %RH
      float p = bme.readPressure() / 100.0f;  // hPa
      String ts = iso8601_utc_ms();

      Serial.print("BME: "); Serial.print(t,1); Serial.print("C  ");
      Serial.print(h,1); Serial.print("%  ");
      Serial.print(p,1); Serial.print(" hPa  | buffered=");
      Serial.println(rbSize());

      // If offline, buffer all three. If online, prefer immediate send
      bool haveBacklog = !rbEmpty();
      bool online = (WiFi.status() == WL_CONNECTED);

      if (!online || haveBacklog) {
        // Buffer the 3 readings atomically (same timestamp)
        rbPush(SENSOR_TEMP, t, ts);
        rbPush(SENSOR_HUM,  h, ts);
        rbPush(SENSOR_PRES, p, ts);
        // Try a quick flush if we just reconnected
        if (online) flushBufferedReadings(20);
      }
      else {
        // No backlog and online: send live
        bool ok1 = sendReadingJson(SENSOR_TEMP, t, ts);
        bool ok2 = sendReadingJson(SENSOR_HUM,  h, ts);
        bool ok3 = sendReadingJson(SENSOR_PRES, p, ts);
        if (!(ok1 && ok2 && ok3)) {
          // If any fails, push all 3 to buffer (so order/timestamp stays consistent)
          rbPush(SENSOR_TEMP, t, ts);
          rbPush(SENSOR_HUM,  h, ts);
          rbPush(SENSOR_PRES, p, ts);
          Serial.println("[API] Live send failed. Switched to buffering.");
        }
      }
    }
  }
}
