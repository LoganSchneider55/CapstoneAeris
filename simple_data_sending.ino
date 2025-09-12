#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <sys/time.h>
#include <time.h>

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
  gettimeofday(&tv, nullptr);         // UTC
  time_t sec = tv.tv_sec;
  struct tm tm_utc;
  gmtime_r(&sec, &tm_utc);
  char base[32];
  strftime(base, sizeof(base), "%Y-%m-%dT%H:%M:%S", &tm_utc);
  char out[40];
  snprintf(out, sizeof(out), "%s.%03ldZ", base, tv.tv_usec / 1000); // ms
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
  WiFiClientSecure client;
  client.setInsecure();               // OK for bring-up; load a CA for production

  HTTPClient http;
  http.setTimeout(15000);             // Render free tier can cold-start
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

bool sendReading(const char* sensor_type, float value) {
  String url = String(API_BASE) + PATH_READINGS;
  String ts  = iso8601_utc_ms();    

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

// ---------------- Setup / Loop ----------------
void setup() {
  Serial.begin(115200);
  delay(100);

  device_id = "esp32";

  // Sensor
  Wire.begin();
  bme_ok = bme.begin(0x76);
  if (!bme_ok) bme_ok = bme.begin(0x77);
  Serial.println(bme_ok ? "BME280 found ✅" : "BME280 not found ❌");

  ensureWiFi();
  setupTimeUTC();
  registerDevice();                   // safe if already registered (409 treated as OK)
}

void loop() {
  
  if (WiFi.status() != WL_CONNECTED) ensureWiFi();

  unsigned long now = millis();
  if (now - lastSample >= SAMPLE_MS) {
    lastSample = now;

    if (bme_ok) {
      float t = bme.readTemperature();        // °C
      float h = bme.readHumidity();           // %RH
      float p = bme.readPressure() / 100.0f;  // hPa

      Serial.print("BME: "); Serial.print(t,1); Serial.print("C  ");
      Serial.print(h,1); Serial.print("%  ");
      Serial.print(p,1); Serial.println(" hPa");

      bool ok1 = sendReading(SENSOR_TEMP, t);
      bool ok2 = sendReading(SENSOR_HUM,  h);
      bool ok3 = sendReading(SENSOR_PRES, p);
      if (!(ok1 && ok2 && ok3)) Serial.println("[API] one or more sends failed.");
    }
  }
}