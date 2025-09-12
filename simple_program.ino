#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

// ---------- Wi-Fi ----------
const char* WIFI_SSID = "Cesar iPhone";
const char* WIFI_PASS = "Yuca12345";

// ---------- BME280 ----------
Adafruit_BME280 bme;
bool bme_ok = false;

// ---------- Timing ----------
unsigned long lastSample = 0;
const unsigned long SAMPLE_MS = 2000;

void setup() {
  Serial.begin(115200);
  delay(100);

  // I2C for BME280
  Wire.begin();
  bme_ok = bme.begin(0x76);
  if (!bme_ok) bme_ok = bme.begin(0x77);

  if (bme_ok) Serial.println("BME280 found");
  else Serial.println("BME280 not found");

  // Wi-Fi connect
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  unsigned long now = millis();
  if (now - lastSample >= SAMPLE_MS) {
    lastSample = now;

    if (bme_ok) {
      float t = bme.readTemperature();
      float h = bme.readHumidity();
      float p = bme.readPressure() / 100.0; // hPa

      Serial.print("Temp: ");
      Serial.print(t, 1);
      Serial.print(" °C | Humidity: ");
      Serial.print(h, 1);
      Serial.print(" % | Pressure: ");
      Serial.print(p, 1);
      Serial.println(" hPa");
    }
  }
}