// src/components/ThresholdTable.js
import React from "react";

const thresholds = {
  "PM2.5 (µg/m³)": [
    { label: "Good", max: 12, color: "green" },
    { label: "Moderate", max: 35.4, color: "goldenrod" },
    { label: "Unhealthy", max: 150.4, color: "orange" },
    { label: "Hazardous", max: Infinity, color: "red" },
  ],
  "CO (ppm)": [
    { label: "Good", max: 4.4, color: "green" },
    { label: "Moderate", max: 9.4, color: "goldenrod" },
    { label: "Unhealthy", max: 12.4, color: "orange" },
    { label: "Hazardous", max: Infinity, color: "red" },
  ],
  "VOC (ppb)": [
    { label: "Good", max: 300, color: "green" },
    { label: "Moderate", max: 1000, color: "goldenrod" },
    { label: "Unhealthy", max: 2900, color: "orange" },
    { label: "Hazardous", max: Infinity, color: "red" },
  ],
  "Temperature (°C)": [
    { label: "Cold", max: 18, color: "blue" },
    { label: "Comfortable", max: 24, color: "green" },
    { label: "Warm", max: 28, color: "orange" },
    { label: "Hot", max: Infinity, color: "red" },
  ],
  "Humidity (%)": [
    { label: "Dry", max: 30, color: "blue" },
    { label: "Comfortable", max: 60, color: "green" },
    { label: "Humid", max: 80, color: "orange" },
    { label: "Very Humid", max: Infinity, color: "red" },
  ],
};

// Helper to format ranges
function formatRange(component, levels, index) {
  const lvl = levels[index];

  if (component === "Temperature (°C)" || component === "Humidity (%)") {
    if (lvl.max === Infinity) return `> ${levels[index - 1].max}`;
    if (index === 0) return `≤ ${lvl.max}`;
    return `${levels[index - 1].max + 1} – ${lvl.max}`;
  } else {
    const min = index === 0 ? 0 : (levels[index - 1].max + 0.1).toFixed(1);
    const max = lvl.max === Infinity ? `> ${levels[index - 1].max}` : lvl.max;
    return `${min} – ${max}`;
  }
}

export default function ThresholdTable() {
  return (
    <div
      style={{
        marginBottom: 30,
        padding: 20,
        borderRadius: 12,
        backgroundColor: "#f9f9f9",
        boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
      }}
    >
      <h3 style={{ marginBottom: 15 }}>Air Quality Reference</h3>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 8 }}>Component</th>
            {Object.entries(thresholds)["PM2.5 (µg/m³)"]?.[1]?.map((_, i) => (
              <th key={i} style={{ padding: 8, textAlign: "center" }}>
                {/* Column headers can stay empty because each row shows its labels */}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.entries(thresholds).map(([component, levels]) => (
            <tr key={component}>
              <td style={{ padding: 8 }}>{component}</td>
              {levels.map((lvl, idx) => (
                <td
                  key={lvl.label}
                  style={{
                    textAlign: "center",
                    padding: 8,
                    backgroundColor: lvl.color + "33",
                    fontWeight: 600,
                    borderRadius: 4,
                  }}
                >
                  {lvl.label} <br />({formatRange(component, levels, idx)})
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
