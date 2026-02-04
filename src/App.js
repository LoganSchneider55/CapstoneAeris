// src/App.js
import React, { useEffect, useState } from "react";
import ReadingCard from "./components/ReadingCard";
import ThresholdTable from "./components/ThresholdTable";
import PM25Chart from "./components/PM25Chart";
import COChart from "./components/COChart";
import VOCChart from "./components/VOCChart";
import TempChart from "./components/TempChart";
import HumidityChart from "./components/HumidityChart";
import { fetchLatest, fetchHistory } from "./lib/api";
import "./index.css";

// Map backend sensor_type -> frontend key
const SENSOR_ALIAS = {
  // particulate
  pm25_ugm3: "pm25",

  // gases
  co_ppm: "co",
  Co_ppm: "co",
  voc_index: "voc",

  // environmental
  temperature_c: "temperature",
  humidity: "humidity",
};

// Keys we actually display/chart
const SENSOR_KEYS = ["pm25", "co", "voc", "temperature", "humidity"];

const EMPTY_HISTORY = {
  pm25: [],
  co: [],
  voc: [],
  temperature: [],
  humidity: [],
};

// Take whatever the backend returns from /latest and normalize it
function normalizeLatest(raw) {
  if (!raw || typeof raw !== "object") return {};

  const out = {};

  // Shape A: { readings: { sensor_type: value, ... }, measured_at: ... }
  if (raw.readings && typeof raw.readings === "object") {
    for (const [sensorType, value] of Object.entries(raw.readings)) {
      const key = SENSOR_ALIAS[sensorType] || sensorType;
      if (SENSOR_KEYS.includes(key) && value != null) {
        out[key] = Number(value);
      }
    }
    if (raw.measured_at) out.measured_at = raw.measured_at;
  }

  // Shape B: flat object like { temperature_c: 23.4, humidity: 40.1, ... }
  for (const [sensorType, value] of Object.entries(raw)) {
    const key = SENSOR_ALIAS[sensorType] || sensorType;
    if (SENSOR_KEYS.includes(key) && value != null) {
      out[key] = Number(value);
    }
  }

  if (!out.measured_at && raw.measured_at) {
    out.measured_at = raw.measured_at;
  }

  return out;
}

// Take whatever /history returns and normalize to
// { pm25:[{timestamp,value}], co:[...], ... }
function normalizeHistory(raw) {
  const out = { ...EMPTY_HISTORY };

  if (!raw) return out;

  // Shape 1: { rows: [{ sensor_type, measured_at, value }, ...] }
  if (Array.isArray(raw.rows)) {
    for (const r of raw.rows) {
      const key = SENSOR_ALIAS[r.sensor_type] || r.sensor_type;
      if (!SENSOR_KEYS.includes(key)) continue;
      out[key].push({
        timestamp: r.measured_at,
        value: Number(r.value ?? 0),
      });
    }
  } else if (typeof raw === "object") {
    // Shape 2: { sensor_type: [{timestamp,value}, ...], ... }
    for (const [sensorType, arr] of Object.entries(raw)) {
      const key = SENSOR_ALIAS[sensorType] || sensorType;
      if (!SENSOR_KEYS.includes(key) || !Array.isArray(arr)) continue;
      out[key] = arr.map((p) => ({
        timestamp: p.timestamp ?? p.measured_at,
        value: Number(p.value ?? 0),
      }));
    }
  }

  // Sort each series by time
  for (const key of SENSOR_KEYS) {
    out[key].sort((a, b) =>
      String(a.timestamp).localeCompare(String(b.timestamp))
    );
  }

  return out;
}

export default function App() {
  const [latest, setLatest] = useState({
    pm25: null,
    co: null,
    voc: null,
    temperature: null,
    humidity: null,
  });

  const [history, setHistory] = useState(EMPTY_HISTORY);

  // Initial load of history + latest
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const [histRaw, latRaw] = await Promise.all([
          // pull ~6 hours of history
          fetchHistory(undefined, 360),
          fetchLatest(),
        ]);

        if (cancelled) return;

        const hist = normalizeHistory(histRaw);
        const lat = normalizeLatest(latRaw);

        setHistory(hist);
        setLatest((prev) => ({ ...prev, ...lat }));
      } catch (err) {
        console.error("Initial load failed:", err);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // Poll latest every 30 seconds and append to history
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const latRaw = await fetchLatest();
        const lat = normalizeLatest(latRaw);
        const ts = lat.measured_at || new Date().toISOString();

        setLatest((prev) => ({ ...prev, ...lat }));

        setHistory((prev) => {
          const next = { ...prev };
          for (const key of SENSOR_KEYS) {
            if (lat[key] == null) continue;
            const arr = next[key] || [];
            next[key] = [
              ...arr.slice(-119), // keep last 120 points
              { timestamp: ts, value: Number(lat[key] ?? 0) },
            ];
          }
          return next;
        });
      } catch (err) {
        console.error("Polling latest failed:", err);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="container" style={{ padding: 20 }}>
      <div className="header" style={{ marginBottom: 20 }}>
        <h1>Air Quality Dashboard</h1>
        <div>Live data from Aeris API</div>
      </div>

      {/* Top Reading Cards */}
      <div
        className="cards-row"
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 20,
          marginBottom: 20,
        }}
      >
        <ReadingCard
          label="PM2.5"
          value={latest.pm25}
          unit="µg/m³"
          history={history.pm25}
        />
        <ReadingCard
          label="VOC"
          value={latest.voc}
          unit="ppb"
          history={history.voc}
        />
        <ReadingCard
          label="CO"
          value={latest.co}
          unit="ppm"
          history={history.co}
        />
        <ReadingCard
          label="Temperature"
          value={latest.temperature}
          unit="°C"
          history={history.temperature}
        />
        <ReadingCard
          label="Humidity"
          value={latest.humidity}
          unit="%"
          history={history.humidity}
        />
      </div>

      {/* System Status */}
      <div
        className="card"
        style={{
          padding: 15,
          borderRadius: 10,
          boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
          marginBottom: 30,
          maxWidth: 400,
        }}
      >
        <h4>System Status</h4>
        <p>Backend: using live API</p>
        <p>Device: {process.env.REACT_APP_DEVICE_ID || "unknown"}</p>
      </div>

      {/* Charts */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 40,
        }}
      >
        <ThresholdTable />
        <PM25Chart data={history.pm25} latest={latest.pm25} />
        <COChart data={history.co} latest={latest.co} />
        <VOCChart data={history.voc} latest={latest.voc} />
        <TempChart data={history.temperature} latest={latest.temperature} />
        <HumidityChart data={history.humidity} latest={latest.humidity} />
      </div>
    </div>
  );
}
