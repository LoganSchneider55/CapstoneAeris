// src/components/ReadingCard.js
import React from "react";



function formatValue(val, decimals = 1) {
  if (val === null || val === undefined) return "--";
  const num = Number(val);
  if (Number.isNaN(num)) return "--";
  return num.toFixed(decimals);
}


function getStatus(label, value) {
  if (value === null || value === undefined) return { text: "—", color: "#333" };

  switch (label) {
    case "PM2.5":
      if (value <= 12) return { text: "Good", color: "green" };
      if (value <= 35.4) return { text: "Moderate", color: "goldenrod" };
      if (value <= 150.4) return { text: "Unhealthy", color: "orange" };
      return { text: "Hazardous", color: "red" };

    case "CO":
      if (value <= 4.4) return { text: "Good", color: "green" };
      if (value <= 9.4) return { text: "Moderate", color: "goldenrod" };
      if (value <= 12.4) return { text: "Unhealthy", color: "orange" };
      return { text: "Hazardous", color: "red" };

    case "VOC":
      if (value <= 300) return { text: "Good", color: "green" };
      if (value <= 1000) return { text: "Moderate", color: "goldenrod" };
      if (value <= 3000) return { text: "Unhealthy", color: "orange" };
      return { text: "Hazardous", color: "red" };

    case "Temperature":
      if (value <= 18) return { text: "Cold", color: "blue" };
      if (value <= 24) return { text: "Comfortable", color: "green" };
      if (value <= 28) return { text: "Warm", color: "orange" };
      return { text: "Hot", color: "red" };

    case "Humidity":
      if (value <= 30) return { text: "Dry", color: "blue" };
      if (value <= 60) return { text: "Comfortable", color: "green" };
      if (value <= 80) return { text: "Humid", color: "orange" };
      return { text: "Very Humid", color: "red" };

    default:
      return { text: "", color: "#333" };
  }
}

const ReadingCard = ({ label, value, unit, history = [] }) => {
  const status = getStatus(label, value);

  // Calculate min, max, avg
  const numbers = history.map((d) => d.value).filter((v) => v !== undefined && v !== null);
  const min = numbers.length ? Math.min(...numbers) : null;
  const max = numbers.length ? Math.max(...numbers) : null;
  const avg = numbers.length ? numbers.reduce((a, b) => a + b, 0) / numbers.length : null;

  return (
    <div className="card" style={{ padding: 10, borderRadius: 10, boxShadow: "0 2px 4px rgba(0,0,0,0.1)" }}>
      <h4 style={{ margin: "0 0 8px 0" }}>{label}</h4>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          <div style={{ fontSize: 20, fontWeight: 600 }}>
            {value !== undefined ? formatValue(value) : "—"} {unit}
          </div>
          <div style={{ color: status.color, fontWeight: 600 }}>{status.text}</div>
        </div>
        {numbers.length > 0 && (
          <div style={{ fontSize: 12, color: "#555" }}>
            Min: {min.toFixed(1)} {unit} | Max: {max.toFixed(1)} {unit} | Avg: {avg.toFixed(1)} {unit}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReadingCard;





